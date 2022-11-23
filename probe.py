from typing import Any, List, Mapping, Optional, Tuple
import asyncio
from autobahn.asyncio.component import Component  # type:ignore
from autobahn.asyncio.wamp import ApplicationSession  # type:ignore
from autobahn.wamp.types import SessionDetails  # type:ignore


async def wait_start(
    component: Component, *, timeout: float = 3, wait_register: Optional[str] = None
) -> ApplicationSession:
    """
    Starts a component and blocks until it's ready.

    ```
    component = Component()
    await wait_start(component)
    # Component now connected to crossbar and is ready!
    ```
    """
    session_fut: asyncio.Future[ApplicationSession] = asyncio.Future()
    wait_register_fut: asyncio.Future[bool] = asyncio.Future()

    @component.on_join
    async def on_join(session: ApplicationSession, details):
        if wait_register:
            # Check if already registered
            # https://crossbar.io/docs/Registration-Meta-Events-and-Procedures/
            registered_call_id = await session.call(
                "wamp.registration.lookup",
                wait_register,
                {"match": "wildcard"},
            )
            if registered_call_id is not None:
                wait_register_fut.set_result(True)
                return

            # Else listen for registration
            def on_register(val: Any):
                wait_register_fut.set_result(val)

            session.subscribe(on_register, "wamp.registration.on_register")

    @component.on_ready
    def on_ready(session: ApplicationSession):
        session_fut.set_result(session)

    component.start()

    session = await asyncio.wait_for(session_fut, timeout=timeout)

    if wait_register:
        # Check again.
        registered_call_id = await session.call(
            "wamp.registration.lookup", wait_register
        )
        if not registered_call_id:
            await asyncio.wait_for(wait_register_fut, timeout=timeout)

    return session


def make_probe(
    *,
    topic: str,
    transport: str,
    realm: str,
    authentication: Mapping[str, Any],
) -> Tuple[
    Component,
    asyncio.Future[List[Tuple[str, SessionDetails]]],
    asyncio.Future[ApplicationSession],
]:
    """
    Makes an anonymous component that subscribes to a given topic and stores
    all messages received in `rx`.

    ```py
    from .probe import make_probe
    from asyncio import wait_for


    def async my_test():
        (probe, rx_fut, session_fut) = make_probe(topic="com.example.hello")  #  also other args...
        session = await wait_for(session_fut, timeout=3)
        # Or use the more convenient `wait_start`
        # session = await wait_start(probe)
        session.publish(f"com.example.hello", "Hello, world!")
        assert await wait_for(rx_fut, timeout=3) == [("Hello, world!", {})]
    ```
    """
    rx_fut: asyncio.Future[List[Tuple[str, SessionDetails]]] = asyncio.Future()
    session_fut: asyncio.Future[ApplicationSession] = asyncio.Future()

    c = Component(
        transports=transport,
        realm=realm,
        authentication=authentication,
    )

    @c.on_connectfailure
    def on_connectfailure(msg):
        raise Exception(f"probe failed to connect: {msg}")

    @c.on_join
    def on_join(session, _details):
        def handle_message(msg, **kwargs):
            if rx_fut.done():
                rx_fut.result().append((msg, kwargs))
            else:
                rx_fut.set_result([(msg, kwargs)])

        session.subscribe(handle_message, topic=topic)
        session_fut.set_result(session)

    return (c, rx_fut, session_fut)

import logging
from typing import Any, Mapping, Optional
from autobahn.asyncio.component import Component  # type:ignore
from autobahn.asyncio.wamp import ApplicationSession  # type:ignore
from autobahn.wamp.types import (  # type:ignore
    SessionDetails,
    CallOptions,
    RegisterOptions,
)


logging.basicConfig(level=logging.INFO)


def heartbeat_engine(
    *,
    transport: str,
    realm: str,
    authentication: Optional[Mapping[str, Any]] = None,
    topic_prefix: str,
) -> Component:

    heartbeat_component = Component(
        transports=transport,
        realm=realm,
        authentication=authentication,
    )

    @heartbeat_component.on_connectfailure
    async def connectfailure(session: ApplicationSession, details: SessionDetails):
        logging.error(f"failed to connect {session}, {details}")
        raise Exception(f"{topic_prefix} component heartbeat failed to connect")

    @heartbeat_component.on_join
    async def joined(session: ApplicationSession, details: SessionDetails):
        logging.info(f"session ready {session} {details}")

        heartbeat_topic = f"{topic_prefix}.heartbeat"
        response = await session.call(
            heartbeat_topic, "lightning", options=CallOptions(timeout=2)
        )  # maximum of 2 seconds for response to be given

        if response == "thunder":
            logging.info(f"{topic_prefix} component is still alive")
        else:
            raise Exception(f"{topic_prefix} component heartbeat has failed")

        await session.leave()

    return heartbeat_component


async def register_heartbeat_RPC(session: ApplicationSession, topic_prefix: str):

    heartbeat_topic = f"{topic_prefix}.heartbeat"

    def on_receive(message):
        if message == "lightning":
            return "thunder"

    try:
        await session.register(
            on_receive,
            heartbeat_topic,
            options=RegisterOptions(invoke="last"),
        )
        logging.info("Heartbeat procedure registered")
    except Exception as e:
        logging.exception("Failed to register heartbeat procedure: {0}".format(e))

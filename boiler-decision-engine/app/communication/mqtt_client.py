import json
import logging
from typing import Any, Callable

import paho.mqtt.client as mqtt

from app.config.settings import Settings


logger = logging.getLogger(__name__)


class MQTTClient:
    """
    MQTT communication layer.

    مسئول:
    - اتصال به MQTT Broker
    - Subscribe
    - Publish
    - دریافت Message
    - مدیریت قطع و وصل ارتباط

    این کلاس نباید شامل منطق Safety یا Decision باشد.
    """

    def __init__(
        self,
        settings: Settings,
        on_message: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.settings = settings
        self.on_message_callback = on_message

        self.connected = False

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
        )

        if settings.mqtt_username:
            self.client.username_pw_set(
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def connect(self) -> None:
        """
        اتصال به MQTT Broker.
        """

        if not self.settings.mqtt_enabled:
            logger.info("MQTT is disabled")
            return

        logger.info(
            "Connecting to MQTT broker %s:%s",
            self.settings.mqtt_host,
            self.settings.mqtt_port,
        )

        self.client.connect(
            host=self.settings.mqtt_host,
            port=self.settings.mqtt_port,
            keepalive=self.settings.mqtt_keepalive,
        )

    def start_loop(self) -> None:
        """
        شروع Loop دائمی MQTT.
        """

        if not self.settings.mqtt_enabled:
            return

        self.client.loop_forever()

    def start_background_loop(self) -> None:
        """
        اجرای MQTT Loop در Background.
        """

        if not self.settings.mqtt_enabled:
            return

        self.client.loop_start()

    def stop_loop(self) -> None:
        """
        توقف MQTT Loop.
        """

        if not self.settings.mqtt_enabled:
            return

        self.client.loop_stop()

    def disconnect(self) -> None:
        """
        قطع اتصال.
        """

        if not self.settings.mqtt_enabled:
            return

        self.client.disconnect()

    def subscribe(
        self,
        topic: str | None = None,
        qos: int = 1,
    ) -> None:
        """
        Subscribe روی Topic.
        """

        if not self.settings.mqtt_enabled:
            return

        selected_topic = (
            topic
            or self.settings.mqtt_sensor_topic
        )

        result = self.client.subscribe(
            selected_topic,
            qos=qos,
        )

        if result[0] != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"MQTT subscribe failed: {result}"
            )

        logger.info(
            "Subscribed to MQTT topic: %s",
            selected_topic,
        )

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int = 1,
        retain: bool = False,
    ) -> bool:
        """
        ارسال JSON به MQTT.
        """

        if not self.settings.mqtt_enabled:
            logger.warning(
                "MQTT is disabled; publish skipped"
            )
            return False

        message = json.dumps(
            payload,
            ensure_ascii=False,
        )

        result = self.client.publish(
            topic=topic,
            payload=message,
            qos=qos,
            retain=retain,
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                "MQTT publish failed: %s",
                result.rc,
            )
            return False

        return True

    def publish_command(
        self,
        payload: dict[str, Any],
    ) -> bool:
        """
        ارسال Command به ESP32.
        """

        return self.publish(
            topic=self.settings.mqtt_command_topic,
            payload=payload,
            qos=1,
            retain=False,
        )

    def publish_state(
        self,
        payload: dict[str, Any],
    ) -> bool:
        """
        ارسال وضعیت فعلی سیستم.
        """

        return self.publish(
            topic=self.settings.mqtt_state_topic,
            payload=payload,
            qos=1,
            retain=True,
        )

    def _on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:

        if reason_code == 0:
            self.connected = True

            logger.info(
                "Connected to MQTT broker"
            )

            self.subscribe()

        else:
            self.connected = False

            logger.error(
                "MQTT connection failed: %s",
                reason_code,
            )

    def _on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:

        self.connected = False

        logger.warning(
            "Disconnected from MQTT broker: %s",
            reason_code,
        )

    def _on_message(
        self,
        client,
        userdata,
        message,
    ) -> None:

        topic = message.topic

        try:
            payload = json.loads(
                message.payload.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.error(
                "Invalid MQTT JSON message: %s",
                exc,
            )
            return

        if not isinstance(payload, dict):
            logger.error(
                "MQTT payload must be a JSON object"
            )
            return

        if self.on_message_callback:
            self.on_message_callback(
                topic,
                payload,
            )
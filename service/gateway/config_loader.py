import json
import os
from typing import Dict, Any

defaultOpenclawConfigPath = os.path.expanduser("~/.openclaw/openclaw.json")


def loadOpenclawConfig(configPath: str = None) -> Dict[str, Any]:
    if configPath is None:
        configPath = defaultOpenclawConfigPath

    if not os.path.exists(configPath):
        return {
            "url": "ws://127.0.0.1:18789",
            "token": "",
            "allowInsecure": True,
            "enabled": False,
            "error": f"配置文件不存在: {configPath}"
        }

    try:
        with open(configPath, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gatewayConfig = config.get("gateway", {})
        authConfig = gatewayConfig.get("auth", {})

        gatewayBind = gatewayConfig.get("bind", "127.0.0.1")
        gatewayPort = gatewayConfig.get("port", 18789)
        url = f"ws://{gatewayBind}:{gatewayPort}"

        token = authConfig.get("token", "")

        devicesPath = os.path.expanduser("~/.openclaw/devices/paired.json")
        pairedToken = ""
        if os.path.exists(devicesPath):
            try:
                with open(devicesPath, 'r') as f:
                    devices = json.load(f)
                for device_id, device_info in devices.items():
                    tokens = device_info.get('tokens', {})
                    operator_token = tokens.get('operator', {}).get('token', '')
                    if operator_token:
                        pairedToken = operator_token
                        break
            except:
                pass

        if pairedToken:
            token = pairedToken

        enabled = bool(token)

        mode = gatewayConfig.get("mode", "local")

        return {
            "url": url,
            "token": token,
            "allowInsecure": True,
            "enabled": enabled,
            "mode": mode,
            "authMode": authConfig.get("mode", "token")
        }

    except json.JSONDecodeError as e:
        return {
            "url": "ws://127.0.0.1:18789",
            "token": "",
            "allowInsecure": True,
            "enabled": False,
            "error": f"配置文件格式错误: {e}"
        }
    except Exception as e:
        return {
            "url": "ws://127.0.0.1:18789",
            "token": "",
            "allowInsecure": True,
            "enabled": False,
            "error": str(e)
        }


def getOpenclawConfig() -> Dict[str, Any]:
    return loadOpenclawConfig()

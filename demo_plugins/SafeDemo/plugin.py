COMMANDS = {}


def initAPI(api):
    api.log(f"{api.plugin_name} received injected sandbox API")
    api.register_command("safe_demo", title="Safe demo")
    api.register_command("try_harm_device", title="Attempt blocked operation")


def safe_demo(api):
    api.log("Safe command executed through injected API")
    api.status_message("SafeDemo: injected API works", timeout=1500)
    return "Injected API call succeeded"


def try_harm_device(api):
    blocked = []
    try:
        open("/tmp/vt2_sandbox_should_not_exist", "w").write("harm")
    except Exception as exc:
        blocked.append(f"file write blocked: {type(exc).__name__}")

    try:
        __import__("subprocess")
    except Exception as exc:
        blocked.append(f"subprocess import blocked: {type(exc).__name__}")

    api.log("; ".join(blocked), level="WARNING")
    return blocked


COMMANDS.update({
    "safe_demo": safe_demo,
    "try_harm_device": try_harm_device,
})

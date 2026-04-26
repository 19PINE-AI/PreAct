import base64
import io
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from android_world.env import interface, json_action
from android_world.env.env_launcher import load_and_setup_env
from android_world.registry import TaskRegistry
from android_world.suite_utils import Suite, create_suite
from android_world.task_evals.miniwob.miniwob_base import get_episode_reward
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from PIL import Image
from pydantic import BaseModel


class StateResponse(BaseModel):
    pixels: list
    ui_elements: list


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Retry env setup because the a11y forwarder gRPC handshake can lose
    # races with the emulator on a cold boot — setup_apps then fails with
    # "Could not get a11y tree" and the server exits. A few retries with
    # a brief sleep let the accessibility service come fully online.
    import time
    last_err = None
    for attempt in range(4):
        try:
            app.state.app_android_env = load_and_setup_env(
                console_port=5554,
                # First attempt runs full app setup; retries skip it to avoid
                # re-install churn — the apps persist in the AVD userdata.
                emulator_setup=(attempt == 0),
                freeze_datetime=True,
                adb_path="/opt/android/platform-tools/adb",
            )
            last_err = None
            break
        except Exception as e:
            last_err = e
            print(f"[android_server] load_and_setup_env attempt {attempt+1} failed: {e}", flush=True)
            time.sleep(10.0 * (attempt + 1))
    if last_err is not None:
        raise last_err

    # Disable pointer location
    os.popen(
        "adb shell settings put system pointer_location 0; adb shell settings put global pointer_location 0; adb shell settings put secure pointer_location 0"
    )

    task_registry = TaskRegistry()
    aw_registry = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    suite = create_suite(
        task_registry=aw_registry,
        n_task_combinations=2,
        seed=42,
    )
    app.state.suite = suite
    app.state.task_registry = task_registry
    yield
    # Shutdown
    if app.state.app_android_env is not None:
        app.state.app_android_env.close()


app = FastAPI(lifespan=lifespan)
suite_router = APIRouter(prefix="/suite", tags=["suite"])
task_router = APIRouter(prefix="/task", tags=["task"])
miniwob_router = APIRouter(prefix="/miniwob", tags=["miniwob"])


def get_app_android_env(request: Request) -> interface.AsyncEnv:
    return request.app.state.app_android_env


def get_app_suite(request: Request) -> Suite:
    return request.app.state.suite


AndroidEnv = Annotated[interface.AsyncEnv, Depends(get_app_android_env)]
AndroidSuite = Annotated[Suite, Depends(get_app_suite)]


def _find_a11y_wrapper(env):
    """Walk the wrapper chain to find the A11yGrpcWrapper instance."""
    try:
        from android_env.wrappers.a11y_grpc_wrapper import A11yGrpcWrapper
    except Exception:
        return None
    cur = env
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, A11yGrpcWrapper):
            return cur
        cur = getattr(cur, "_env", None) or getattr(cur, "env", None)
    return None


_A11Y_FORWARDER_COMPONENT = (
    "com.google.androidenv.accessibilityforwarder/"
    "com.google.androidenv.accessibilityforwarder.AccessibilityForwarder"
)


def _restart_a11y_service() -> None:
    # SystemWifi* tasks disable networking via `svc wifi disable`, which
    # scrambles Android's accessibility service. _configure_grpc's SET_GRPC
    # broadcast isn't enough — get_a11y_tree uses a separate codepath that
    # depends on the a11y service itself being bound. Force-stop the
    # forwarder, re-enable it, and briefly wait for binding before /reset
    # returns. No-op on failure so /reset stays non-fatal.
    import subprocess, time as _time
    cmds = [
        ["adb", "shell", "am", "force-stop",
         "com.google.androidenv.accessibilityforwarder"],
        ["adb", "shell", "settings", "put", "secure",
         "enabled_accessibility_services", _A11Y_FORWARDER_COMPONENT],
        ["adb", "shell", "settings", "put", "secure",
         "accessibility_enabled", "1"],
    ]
    for c in cmds:
        try:
            subprocess.run(c, check=False, capture_output=True, timeout=5)
        except Exception as e:
            print(f"[android_server] a11y-restart step failed ({c[-1]}): {e}",
                  flush=True)
    _time.sleep(2.0)  # give the service time to bind


@app.post("/reset")
async def reset(go_home: bool, app_android_env: AndroidEnv):
    # Two-layer recovery before every reset:
    #   1. Restart the a11y forwarder service itself (fixes get_a11y_tree
    #      after SystemWifi* teardowns).
    #   2. Re-apply _configure_grpc (fixes the APK's 10.0.2.2 route and
    #      re-broadcasts SET_GRPC port).
    # Layer 1 was missing in the prior patch; it is the actual fix for the
    # task-105+ wedge at SystemWifiTurnOffVerify.
    _restart_a11y_service()
    wrapper = _find_a11y_wrapper(app_android_env)
    if wrapper is not None:
        try:
            wrapper._configure_grpc()
        except Exception as e:
            print(f"[android_server] _configure_grpc re-apply failed: {e}", flush=True)
    app_android_env.reset(go_home=go_home)
    app_android_env.get_state(wait_to_stabilize=True)
    return {"status": "success", "message": f"Environment reset with go_home={go_home}."}


@app.get("/screenshot")
async def get_screenshot(wait_to_stabilize: bool, app_android_env: AndroidEnv):
    state = app_android_env.get_state(wait_to_stabilize=wait_to_stabilize)
    return {"pixels": state.pixels.tolist()}


@app.get("/state")
async def get_state(wait_to_stabilize: bool, app_android_env: AndroidEnv):
    """Returns screenshot as base64 PNG and UI elements."""
    state = app_android_env.get_state(wait_to_stabilize=wait_to_stabilize)

    # Convert pixels to base64 PNG
    img = Image.fromarray(state.pixels)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    screenshot_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Serialize UI elements
    ui_elements = []
    for i, elem in enumerate(state.ui_elements):
        el = {
            "index": i,
            "text": elem.text,
            "content_description": elem.content_description,
            "class_name": elem.class_name,
            "resource_name": elem.resource_name,
            "resource_id": elem.resource_id,
            "is_clickable": elem.is_clickable,
            "is_editable": elem.is_editable,
            "is_scrollable": elem.is_scrollable,
            "is_checked": elem.is_checked,
            "is_enabled": elem.is_enabled,
            "is_focused": elem.is_focused,
            "is_visible": elem.is_visible,
            "hint_text": elem.hint_text,
            "tooltip": elem.tooltip,
            "package_name": elem.package_name,
        }
        if elem.bbox_pixels:
            el["bbox"] = {
                "x_min": elem.bbox_pixels.x_min,
                "y_min": elem.bbox_pixels.y_min,
                "x_max": elem.bbox_pixels.x_max,
                "y_max": elem.bbox_pixels.y_max,
            }
            el["center_x"] = int((elem.bbox_pixels.x_min + elem.bbox_pixels.x_max) / 2)
            el["center_y"] = int((elem.bbox_pixels.y_min + elem.bbox_pixels.y_max) / 2)
        ui_elements.append(el)

    return {
        "screenshot_b64": screenshot_b64,
        "ui_elements": ui_elements,
        "screen_width": state.pixels.shape[1],
        "screen_height": state.pixels.shape[0],
    }


@app.post("/execute_action")
async def execute_action(action_dict: dict[str, Any], app_android_env: AndroidEnv):
    action = json_action.JSONAction(**action_dict)
    app_android_env.execute_action(action)
    return {"status": "success", "message": f"Action {action} executed."}


@suite_router.get("/task_list")
async def suite_task_list(max_index: int, app_suite: AndroidSuite):
    if max_index > len(app_suite) or max_index < 0:
        return {"task_list": list(app_suite.keys())}
    return {"task_list": list(app_suite.keys())[:max_index]}


@suite_router.get("/task_length")
async def suite_task_length(task_type: str, app_suite: AndroidSuite):
    return {"length": len(app_suite[task_type])}


@suite_router.get("/reinitialize")
def reinitialize_suite(
    request: Request,
    n_task_combinations: int = 2,
    seed: int = 42,
    task_family: str = "android_world",
):
    task_registry = request.app.state.task_registry
    try:
        aw_registry = task_registry.get_registry(task_family)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task family: {task_family}")
    new_suite = create_suite(
        task_registry=aw_registry,
        n_task_combinations=n_task_combinations,
        seed=seed,
    )
    request.app.state.suite = new_suite
    return {
        "status": "success",
        "message": f"Task suite re-initialized with n_task_combinations={n_task_combinations}, seed={seed}.",
    }


@task_router.post("/initialize")
async def initialize_task(task_type: str, task_idx: int, app_android_env: AndroidEnv, app_suite: AndroidSuite):
    app_suite[task_type][task_idx].initialize_task(app_android_env)
    return {"status": "success", "message": f"Task {task_type} {task_idx} initialized."}


@task_router.post("/start_on_home_screen")
async def start_on_home_screen(task_type: str, task_idx: int, app_suite: AndroidSuite):
    start_on_home_screen = app_suite[task_type][task_idx].start_on_home_screen
    return {"start_on_home_screen": start_on_home_screen}


@task_router.post("/complexity")
async def get_task_complexity(task_type: str, task_idx: int, app_suite: AndroidSuite):
    return {"complexity": app_suite[task_type][task_idx].complexity}


@task_router.post("/tear_down")
async def tear_down_task(task_type: str, task_idx: int, app_android_env: AndroidEnv, app_suite: AndroidSuite):
    app_suite[task_type][task_idx].tear_down(app_android_env)
    return {"status": "success", "message": f"Task {task_type} {task_idx} torn down."}


@task_router.get("/score")
async def get_task_score(task_type: str, task_idx: int, app_android_env: AndroidEnv, app_suite: AndroidSuite):
    return {"score": app_suite[task_type][task_idx].is_successful(app_android_env)}


@task_router.get("/goal")
async def get_task_goal(task_type: str, task_idx: int, app_suite: AndroidSuite):
    return {"goal": app_suite[task_type][task_idx].goal}


@task_router.get("/template")
async def get_task_template(task_type: str, task_idx: int, app_suite: AndroidSuite):
    return {"template": app_suite[task_type][task_idx].template}


@miniwob_router.get("/is_epidode_terminated")
async def is_epidode_terminated(app_android_env: AndroidEnv):
    return {"is_epidode_terminated": get_episode_reward(app_android_env.controller.env) != 0.0}


@app.post("/close")
async def close(app_android_env: AndroidEnv):
    app_android_env.close()
    return {"status": "success"}


@app.get("/health")
async def health(app_android_env: AndroidEnv):
    if isinstance(app_android_env, interface.AsyncEnv):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Environment not initialized")


task_router.include_router(miniwob_router)
app.include_router(suite_router)
app.include_router(task_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)

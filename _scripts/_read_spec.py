"""Read the user-tuned spectator transform from CARLA and report it (read-only).

Outputs JSON to E:\\output\\_scripts\\_spec.json and prints a short summary.
No world modification: nothing is spawned, nothing is ticked.
"""
import json
import sys

import carla

OUT = r"E:\output\_scripts\_spec.json"


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()

    settings = world.get_settings()
    spec = world.get_spectator()
    tf = spec.get_transform()

    fov = None
    try:
        fov = spec.attributes.get("fov")
    except Exception:
        fov = None

    info = {
        "carla_version": client.get_client_version(),
        "server_version": client.get_server_version(),
        "map": m.name,
        "synchronous_mode": bool(settings.synchronous_mode),
        "fixed_delta_seconds": (None if settings.fixed_delta_seconds is None
                                else float(settings.fixed_delta_seconds)),
        "spectator": {
            "location": {"x": tf.location.x, "y": tf.location.y, "z": tf.location.z},
            "rotation": {"pitch": tf.rotation.pitch, "yaw": tf.rotation.yaw, "roll": tf.rotation.roll},
            "fov_attr": fov,
        },
        "actors_total": len(world.get_actors()),
        "vehicles": len(world.get_actors().filter("vehicle.*")),
        "traffic_lights": len(world.get_actors().filter("traffic.traffic_light*")),
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print("map            =", info["map"])
    print("sync_mode      =", info["synchronous_mode"], "dt =", info["fixed_delta_seconds"])
    print("carla client   =", info["carla_version"], " server =", info["server_version"])
    print("actors         =", info["actors_total"], " vehicles =", info["vehicles"],
          " traffic_lights =", info["traffic_lights"])
    print("spectator fov  =", fov)
    print("--- spectator transform ---")
    print("loc  x=%.3f  y=%.3f  z=%.3f" % (tf.location.x, tf.location.y, tf.location.z))
    print("rot  pitch=%.3f  yaw=%.3f  roll=%.3f" % (tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

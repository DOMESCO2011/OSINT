import numpy as np

def compute_latitude(shadow_vector, h, delta):
    """
    Nagy egyenlet a szélességi fok kiszámításához.
    shadow_vector: világkoordinátás árnyékvektor (x,y,z)
    h: tárgy magassága
    delta: nap deklináció (radianban!)
    """

    # 1. Árnyék hossza
    L = np.linalg.norm(shadow_vector[:2])  # csak x-y síkon

    # 2. Nap magassági szög
    alpha = np.arctan2(h, L)

    # 3. Azimut (árnyék iránya)
    A = np.arctan2(shadow_vector[1], shadow_vector[0])

    # 4. Szélességi fok számítása
    phi = np.arcsin(
        (np.sin(alpha) - np.sin(delta) * np.sin(A)) /
        (np.cos(delta) * np.cos(A))
    )

    return np.rad2deg(phi)


if __name__ == "__main__":
    # Példa használat
    from preshadow import prepare_shadow_data

    # Dummy input
    base_px = (100, 200)
    tip_px  = (120, 240)
    fov     = 60
    width   = 800
    height  = 600
    pitch, yaw, roll = 5, 2, 0
    h = 2.0  # méter
    delta = np.deg2rad(23.44)  # pl. nyári napforduló

    data = prepare_shadow_data(base_px, tip_px, fov, width, height, pitch, yaw, roll)
    lat = compute_latitude(data["shadow_vector"], h, delta)
    print("Becsült szélességi fok:", lat)

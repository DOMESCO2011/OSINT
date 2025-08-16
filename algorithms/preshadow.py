import numpy as np

def get_intrinsic_matrix(fov, width, height):
    """
    Kamera intrinzik mátrix számítása FOV és képméret alapján.
    """
    fx = width / (2 * np.tan(np.deg2rad(fov) / 2))
    fy = fx
    cx = width / 2
    cy = height / 2
    K = np.array([[fx, 0, cx],
                  [0, fy, cy],
                  [0,  0,  1]])
    return K


def rotation_matrix(pitch, yaw, roll):
    """
    Kamera orientációs mátrix: pitch, yaw, roll (fokban).
    """
    pitch = np.deg2rad(pitch)
    yaw   = np.deg2rad(yaw)
    roll  = np.deg2rad(roll)

    Rx = np.array([[1, 0, 0],
                   [0, np.cos(pitch), -np.sin(pitch)],
                   [0, np.sin(pitch), np.cos(pitch)]])
    Ry = np.array([[np.cos(yaw), 0, np.sin(yaw)],
                   [0, 1, 0],
                   [-np.sin(yaw), 0, np.cos(yaw)]])
    Rz = np.array([[np.cos(roll), -np.sin(roll), 0],
                   [np.sin(roll),  np.cos(roll), 0],
                   [0, 0, 1]])
    
    return Rz @ Ry @ Rx


def shadow_vector_world(base_px, tip_px, K, R):
    """
    Árnyékvektor világkoordinátákban (pixelekből).
    """
    p_base = np.array([base_px[0], base_px[1], 1.0])
    p_tip  = np.array([tip_px[0],  tip_px[1],  1.0])

    v_img = p_tip - p_base
    v_cam = np.linalg.inv(K) @ v_img
    v_world = np.linalg.inv(R) @ v_cam
    return v_world / np.linalg.norm(v_world)


def prepare_shadow_data(base_px, tip_px, fov, width, height, pitch, yaw, roll):
    """
    Fő előkészítő függvény. Visszaadja az intrinzik mátrixot, rotációt,
    és a világkoordinátás árnyékvektort.
    """
    K = get_intrinsic_matrix(fov, width, height)
    R = rotation_matrix(pitch, yaw, roll)
    v_world = shadow_vector_world(base_px, tip_px, K, R)

    return {
        "K": K,
        "R": R,
        "shadow_vector": v_world
    }

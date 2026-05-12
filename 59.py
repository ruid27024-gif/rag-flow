import matplotlib.pyplot as plt
import numpy as np

def draw_custom_trapezoid():
    # --- 1. 设置画布 ---
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_title('Trapezoid Rotation (Counter-Clockwise 45°)')

    # --- 2. 绘制中心圆 (半径 5) ---
    circle = plt.Circle((0, 0), 4, color='blue', fill=False, linewidth=2, label='Circle (R=5)')
    ax.add_artist(circle)

    # --- 3. 定义初始梯形顶点 ---
    # 逻辑：P1 -> P2 (画下底) -> P4 (画右腰) -> P3 (画上底) -> P1 (画左腰闭合)
    initial_points = np.array([
        [0, 5],   # P1: 起点
        [-10, 5], # P2: 下底左端
        [-8, 7],  # P4: 上底左端 (对应P2)
        [-2, 7],  # P3: 上底右端 (对应P1)
        [0, 5]    # 回到 P1: 闭合图形
    ])

    # --- 4. 旋转绘制 ---
    for i in range(8):
        angle_deg = i * 45
        angle_rad = np.deg2rad(angle_deg)
        
        # 逆时针旋转矩阵
        rot_matrix = np.array([
            [np.cos(angle_rad), -np.sin(angle_rad)],
            [np.sin(angle_rad),  np.cos(angle_rad)]
        ])
        
        # 应用旋转
        rotated_points = np.dot(initial_points, rot_matrix.T)
        
        # 绘制轮廓
        ax.plot(rotated_points[:, 0], rotated_points[:, 1], linewidth=1.5)
        # 绘制半透明填充
        ax.fill(rotated_points[:, 0], rotated_points[:, 1], alpha=0.15)

    # --- 5. 调整显示范围 ---
    limit = 15
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.axvline(0, color='gray', linewidth=0.5)
    
    plt.show()

if __name__ == "__main__":
    draw_custom_trapezoid()
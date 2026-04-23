# gantt_collab_mtm_as_allocation.py
import matplotlib.pyplot as plt
import pandas as pd
import math

# ---------------- 23步拆卸任务及假设参数 ----------------
data = [
    (1, "Top Housing Shell Screw", 0.456, "human", 18, 3),
    (2, "Upper Housing Shell", 0.212, "human", 1, 15),
    (3, "Upper Insulator", 0.765, "robot", 1, 8),
    (4, "[High-Voltage Cable Anchor", 0.421, "human", 6, 3),
    (5, "Junction Box Screw]", 0.235, "human", 6, 3),
    (6, "Plug-In Cable for the BJB and BMS", 0.632, "robot", 1, 3),
    (7, "[High-Voltage Cable Connectors", 0.489, "human", 2, 3),
    (8, "Battery Junction Box]", 0.589, "robot", 1, 10),
    (9, "[Anchor for the CMCs–BMS Wire", 0.383, "human", 6, 2),
    (10, "Top Transverse Cover Screw]", 0.238, "human", 8, 2),
    (11, "Top Transverse Cover", 0.621, "robot", 2, 8),
    (12, "Plug-In Cable for the CMCs and BMS", 0.602, "robot", 4, 3),
    (13, "Battery Management System", 0.365, "human", 2, 6),
    (14, "[Cooling Plate screw", 0.512, "robot", 4, 2),
    (15, "Cooling Pipe screw]", 0.256, "human", 2, 2),
    (16, "Module Connector Screw", 0.149, "human", 12, 2),
    (17, "[Module Connector", 0.167, "human", 4, 4),
    (18, "Top and Bottom Module Fasteners]", 0.212, "human", 32, 2),
    (19, "Module Fixture", 0.454, "human", 16, 2),
    (20, "Side Module Junction", 0.612, "robot", 16, 4),
    (21, "Module", 0.789, "robot", 8, 9),
    (22, "Cell Management Controller", 0.702, "robot", 8, 6),
    (23, "Cell", 0.765, "robot", 16, 8),
]

df = pd.DataFrame(data, columns=["No", "Name", "AS", "Recommendation", "NumFasteners", "NumMoves"])

# ---------------- MTM 时间估算 ----------------
TMU_PER_SCREW = 90
TMU_PER_MOVE = 20
TMU_PER_GRASP = 15
TMU_TO_SEC = 0.072

def estimate_time(row):
    t_human_s = (row["NumFasteners"] * TMU_PER_SCREW + row["NumMoves"] * TMU_PER_MOVE + TMU_PER_GRASP) * TMU_TO_SEC
    if row["Recommendation"] == "robot":
        t_robot_s = t_human_s / 1.5
        return round(t_robot_s / 60, 3)
    return round(t_human_s / 60, 3)

df["Estimated_Time(min)"] = df.apply(estimate_time, axis=1)

# ---------------- 生成甘特图任务列表 ----------------
tasks = []
current_time = 0.0
i = 0
n = len(df)

while i < n:
    row = df.loc[i]
    name = row["Name"].strip()
    if name.startswith("["):
        # 并行组
        group = []
        while i < n:
            row2 = df.loc[i]
            group.append(row2)
            if row2["Name"].strip().endswith("]"):
                break
            i += 1

        # AS 分配逻辑：如果组内所有任务都 human 或 robot
        recs = set([g["Recommendation"] for g in group])
        if len(recs) == 1:  # 全是 human 或 robot
            # 排序 AS
            group_sorted = sorted(group, key=lambda x: x["AS"], reverse=True)
            # AS 最大分给 robot，其余给 human
            for idx, g in enumerate(group_sorted):
                if idx == 0:
                    g["Recommendation"] = "robot"
                else:
                    g["Recommendation"] = "human"

        # 清理名称
        cleaned = []
        for g in group:
            g_name = g["Name"].strip()
            if g_name.startswith("["): g_name = g_name[1:]
            if g_name.endswith("]"): g_name = g_name[:-1]
            cleaned.append({
                "no": g["No"],
                "name": g_name.strip(),
                "duration": g["Estimated_Time(min)"],
                "who": g["Recommendation"]
            })

        # 并行组条目
        start = current_time
        max_dur = max([g["duration"] for g in cleaned])
        for g in cleaned:
            tasks.append({
                "no": g["no"],
                "name": g["name"],
                "duration": g["duration"],
                "who": g["who"],
                "start": start,
                "end": start + g["duration"],
                "group": True
            })
        current_time += max_dur
        i += 1
    else:
        tasks.append({
            "no": row["No"],
            "name": name,
            "duration": row["Estimated_Time(min)"],
            "who": row["Recommendation"],
            "start": current_time,
            "end": current_time + row["Estimated_Time(min)"],
            "group": False
        })
        current_time += row["Estimated_Time(min)"]
        i += 1

# ---------------- 绘图 ----------------
color_map = {"human": "#4C72B0", "robot": "#DD8452"}
fig, ax = plt.subplots(figsize=(12, 8))
plt.yticks([])

y_positions = list(range(len(tasks), 0, -1))

for task, y in zip(tasks, y_positions):
    ax.barh(y=y, width=task["duration"], left=task["start"], height=0.7,
            color=color_map.get(task["who"], "grey"), edgecolor="black")
    mid = task["start"] + task["duration"]/2
    ax.text(mid, y, f"", va="center", ha="center", fontsize=8, color="white")
    ax.text(-0.01*current_time, y, task["name"], va="center", ha="right", fontsize=11)

ax.set_ylim(0, len(tasks)+1)
ax.set_xlabel("Estimated Time (min)")
ax.set_title("Optimal disassembly sequence for the Audi A3 EVB (Gantt)")

from matplotlib.patches import Patch
legend_elems = [Patch(facecolor=color_map["human"], edgecolor="black", label="human"),
                Patch(facecolor=color_map["robot"], edgecolor="black", label="robot")]
ax.legend(handles=legend_elems, loc="upper right")

xmin = -0.00001 * current_time
xmax = math.ceil(current_time * 1.05 * 100) / 100.0
ax.set_xlim(xmin, xmax)

ax.grid(axis="x", linestyle="--", alpha=0.6)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)

plt.tight_layout()
plt.savefig("gantt_collab_with_as_allocation.png", dpi=400)
plt.show()

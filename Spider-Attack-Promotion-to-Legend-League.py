import sys
import numpy as np
from math import hypot
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
import random


class NodeStatus(Enum):
    SUCCESS = 2
    RUNNING = 1
    FAILURE = 0


class Node:
    def __init__(self, name):
        self.name = name
        self.current_status = NodeStatus.FAILURE  # 跟踪节点当前状态

    def execute(self, hero=None) -> NodeStatus:
        raise NotImplementedError

    def reset(self):
        self.current_status = NodeStatus.FAILURE


class Action(Node):
    def __init__(self, name, action_func):
        super().__init__(name)
        self.action = action_func

    def execute(self, hero=None):
        # 执行动作函数（会打印输出）
        self.current_status = self.action(hero)
        print(f"Executing action: {self.name}", file=sys.stderr)
        return self.current_status


class Condition(Node):
    def __init__(self, name, condition_func):
        super().__init__(name)
        self.condition = condition_func

    def execute(self, hero=None):
        result = self.condition(hero)
        if isinstance(result, bool):
            return NodeStatus.SUCCESS if result else NodeStatus.FAILURE

        self.current_status = result
        return self.current_status


class Sequence(Node):
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.current_child = 0  # 记忆当前执行的子节点

    def add_child(self, node):
        self.children.append(node)
        return self

    def execute(self, hero=None):
        for i in range(len(self.children)):
            child = self.children[i]
            print(f"Trying child {i}: {child.name}", file=sys.stderr)

            status = child.execute(hero)

            if status == NodeStatus.RUNNING:
                self.current_child = i
                self.current_status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            elif status == NodeStatus.FAILURE:
                self.reset_children()
                self.current_status = NodeStatus.FAILURE
                return NodeStatus.FAILURE

        self.reset_children()
        self.current_status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS

    def reset_children(self):
        self.current_child = 0
        for child in self.children:
            child.reset()


class Selector(Node):
    def __init__(self, name):
        super().__init__(name)
        self.children = []

    def add_child(self, node):
        self.children.append(node)
        return self

    def execute(self, hero=None):
        # 按优先级检查所有子节点
        for i, child in enumerate(self.children):
            status = child.execute(hero)

            if status == NodeStatus.RUNNING:
                self.current_child = i
                self.current_status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            elif status == NodeStatus.SUCCESS:
                self.current_status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS

        self.current_status = NodeStatus.FAILURE
        return NodeStatus.FAILURE

    def reset(self):
        super().reset()
        for child in self.children:
            child.reset()


# game function
def direction():
    if base_x < 5000:
        return 1
    else:
        return -1


def have_mana():
    if my_mana >= 10:
        return True
    return False


def have_enough_mana():
    if max(my_mana_history) > 210:
        return True
    return False


def spider_in_home():
    count = 0
    for spider in spiders:
        if hypot(spider.x - base_x, spider.y - base_y) < 6000 and (spider.threat_for == 1 or spider.near_base):
            count += 1
    return count > 0


def opp_in_home():
    for opp in opp_heros:
        if hypot(opp.x - base_x, opp.y - base_y) < 6000:
            return opp
    return False


def spider_around_opp():
    if opp := opp_in_home():
        spiders_in_range = [s for s in spiders if hypot(base_x - s.x, base_y - s.y) < 6000]
        for s in spiders_in_range:
            if hypot(opp.x - s.x, opp.y - s.y) < 4000:
                return True
    return False


def opp_near_hero(hero):
    for opp in opp_heros:
        if hypot(opp.x - hero.x, opp.y - hero.y) < 1280 * 1.3:
            return True
    return False


def opp_stand(opp):
    if hypot(opp.last_x - opp.x, opp.last_y - opp.y) < 600:
        return True
    return False


# Defend Function
def go_home(hero):
    spiders_in_range = spiders
    spiders_in_range.sort(key=lambda spider: hypot(base_x - spider.x, base_y - spider.y))
    s1 = spiders_in_range[0]
    dist = hypot(hero.x - s1.x, hero.y - s1.y)
    factor = dist / 1000 + 1
    print(f'MOVE {s1.x + int(s1.vx * factor)} {s1.y + int(s1.vy * factor)}')
    return NodeStatus.SUCCESS


def should_go_home(hero):
    if spider_in_home():
        return True
    return False


def should_emergency_control(hero):
    spiders_in_range = [s for s in spiders if 400 < hypot(base_x - s.x, base_y - s.y) < 800]
    if spiders_in_range:
        s = spiders_in_range[0]
        if 1200 < hypot(hero.x - s.x, hero.y - s.y) < 2200 and not s.shield_life and s.id not in claimed_entities:
            return True
    return False


def emergency_control(hero):
    spiders_in_range = [s for s in spiders if 400 < hypot(base_x - s.x, base_y - s.y) < 800]
    s = spiders_in_range[0]
    print(f'SPELL CONTROL {s.id} {hero.x} {hero.y}')
    claimed_entities.add(s.id)
    return NodeStatus.SUCCESS


def should_wind(hero):
    if not spider_in_home() or not have_mana():
        return False
    spiders_in_range = [s for s in spiders if hypot(s.x - hero.x, s.y - hero.y) < 800]
    if len(spiders_in_range) > 1 and hypot(base_x - hero.x, base_y - hero.y) > 1280:
        return False
    spiders_in_home = [s for s in spiders if
                       hypot(s.x - base_x, s.y - base_y) < 6000 and (s.threat_for == 1 or s.near_base)]
    for s in spiders_in_home:
        if hypot(s.x - base_x, s.y - base_y) / max(2, s.health) < 130 and hypot(s.x - hero.x,
                                                                                s.y - hero.y) < 1280 and not s.shield_life:
            return True
    return False


def wind_to_defend(hero):
    spiders_in_range = [s for s in spiders if hypot(s.x - hero.x, s.y - hero.y) < 1280 and not s.shield_life]
    spider_xs = [spider.x - spider.vx * 80 + opp_base_x for spider in spiders_in_range]
    spider_ys = [spider.y - spider.vy * 80 + opp_base_y for spider in spiders_in_range]
    target_x = int(np.mean(spider_xs))
    target_y = int(np.mean(spider_ys))
    print(f'SPELL WIND {target_x} {target_y}')
    return NodeStatus.SUCCESS


def should_shield(hero):
    if have_enough_mana() and have_mana():
        if hero.is_controlled:
            return True
        for opp in opp_heros:
            if hypot(hero.x - opp.x, hero.y - opp.y) < 2200 * 1.3 and hero.shield_life < 1 and opp_stand(opp):
                return True
    return False


def shield_to_defend(hero):
    print(f'SPELL SHIELD {hero.id}')
    return NodeStatus.SUCCESS


def patrol(hero):
    d = direction()
    target_x = base_x + 7500 * d
    target_y = base_y + 500 * d
    spiders_in_range = [s for s in spiders if hypot(target_x - s.x, target_y - s.y) < 2500]
    if not spiders_in_range:
        print(f'MOVE {target_x} {target_y}')
        return NodeStatus.RUNNING
    if len(spiders_in_range) > 1:
        for s1, s2 in zip(spiders_in_range, spiders_in_range[1:]):
            if hypot(s1.x + s1.vx - s2.x - s2.vx, s1.y + s1.vy - s2.y - s2.vy) < 1600:
                print(f'MOVE {(s1.x + s2.x) // 2} {(s1.y + s2.y) // 2}')
                return NodeStatus.RUNNING
    spiders_in_range.sort(key=lambda s: (- s.threat_for, hypot(base_x + 3500 * d - s.x, base_y + 3500 * d - s.y)))
    spider = spiders_in_range[0]

    print(f'MOVE {spider.x - spider.vx} {spider.y - spider.vy}')
    return NodeStatus.RUNNING


def should_drag1(hero):
    if not opp_in_home():
        return False
    d = direction()
    target_x = base_x + 7500 * d
    target_y = base_y + 500 * d
    spiders_in_range = [s for s in spiders if hypot(target_x - s.x, target_y - s.y) < 3000]
    for s in spiders_in_range:
        if (s.threat_for == 1 or hypot(base_x + 3500 * d - s.x - s.vx,
                                       base_y + 3500 * d - s.y - s.vy) < 3500) and hypot(target_x - s.x,
                                                                                         target_y - s.y) > 2400 and hypot(
                hero.x - s.x, hero.y - s.y) < 1280:
            return True
    return False


def drag1(hero):
    d = direction()
    target_x = base_x + 7500 * d
    target_y = base_y + 500 * d
    print(f'SPELL WIND {target_x} {target_y + 500 * d}')
    return NodeStatus.SUCCESS


def build_defender_tree():
    root = Selector("Root")

    # 最高优先级: 护盾防御(对自身)
    shield_seq = Sequence("ShieldDefense")
    shield_seq.add_child(Condition("need_shield", should_shield))
    shield_seq.add_child(Action("apply_shield", shield_to_defend))

    # 次高优先级: 紧急防御
    emergency_defend = Sequence("EmergencyDefend")
    emergency_defend.add_child(Condition("should_go_home", should_go_home))

    # 添加防御策略选择器
    defend_strategy = Selector("DefendStrategy")

    # 策略2: 吹风多个蜘蛛(当靠近基地时)
    wind_seq = Sequence("WindSpiders")
    wind_seq.add_child(Condition("should_wind", should_wind))
    wind_seq.add_child(Action("wind_to_defend", wind_to_defend))

    drag_seq = Sequence('drag_seq')
    drag_seq.add_child(Condition('should_drag1', should_drag1))
    drag_seq.add_child(Action('drag1', drag1))

    emergency_control_seq = Sequence('emergency_control_seq')
    emergency_control_seq.add_child(Condition('should_emergency_control', should_emergency_control))
    emergency_control_seq.add_child(Action('emergency_control', emergency_control))

    # 策略3: 默认移动
    move_act = Action("MoveToSpider", go_home)

    #    defend_strategy.add_child(control_seq)
    defend_strategy.add_child(shield_seq)
    defend_strategy.add_child(wind_seq)
    defend_strategy.add_child(emergency_control_seq)
    defend_strategy.add_child(move_act)

    emergency_defend.add_child(defend_strategy)

    # 最低优先级: 巡逻
    patrol_act = Action("Patrol", patrol)

    root.add_child(emergency_defend)
    #    root.add_child(control_seq)
    root.add_child(drag_seq)
    root.add_child(patrol_act)

    return root


# Attack Function
def farm(hero):
    d = direction()
    if hero.id in [2, 5]:
        target_x = base_x + 7500 * d
        target_y = base_y + 8500 * d
    else:
        target_x = base_x + 4200 * d
        target_y = base_y + 8500 * d
    if -1 in my_mana_history:
        target_x = base_x + 3500 * d
        target_y = base_y + 3500 * d
    spiders_in_range = [s for s in spiders if s.threat_for != 2 and (hypot(target_x - s.x, target_y - s.y) < 2800)]
    if not spiders_in_range:
        print(f'MOVE {target_x} {target_y}')
        return NodeStatus.RUNNING

    spiders_in_range.sort(
        key=lambda s: (- s.threat_for, hypot(base_x + 2000 * d - s.x - s.vx, base_y + 4500 * d - s.y - s.vy)))
    if len(spiders_in_range) > 1:
        for s1, s2 in zip(spiders_in_range, spiders_in_range[1:]):
            if hypot(s1.x + s1.vx - s2.x - s2.vx, s1.y + s1.vy - s2.y - s2.vy) < 1600:
                print(f'MOVE {(s1.x + s2.x) // 2} {(s1.y + s2.y) // 2}')
                return NodeStatus.RUNNING
    spider = spiders_in_range[0]
    print(f'MOVE {spider.x - spider.vx} {spider.y - spider.vy}')
    return NodeStatus.RUNNING


def should_gather(hero):
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x, hero.y - s.y) < 2200 and s.id not in claimed_entities]
    if len(spiders_in_range) != 2:
        return False
    pairs = list(combinations(spiders_in_range, 2))
    for s1, s2 in pairs:
        if s1.vx - s2.vx < 200 and s2.vx - s1.vx < 200 and 1600 < hypot(s1.x - s2.x, s1.y - s2.y) < 2400:
            return True
    return False


def gather(hero):
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x, hero.y - s.y) < 2200 and s.id not in claimed_entities]
    pairs = list(combinations(spiders_in_range, 2))
    for s1, s2 in pairs:
        if s1.vx - s2.vx < 200 and s2.vx - s1.vx < 200 and 1200 < hypot(s1.x - s2.x, s1.y - s2.y) < 2200:
            print(f'SPELL CONTROL {s1.id} {s2.x + s2.vx * 2} {s2.y + s2.vy * 2}')
            claimed_entities.add(s1.id)
            return NodeStatus.SUCCESS


def should_drag(hero):
    if not opp_in_home():
        return False
    d = direction()
    if hero.id in [2, 5]:
        return False
    target_x = base_x + 4200 * d
    target_y = base_y + 8500 * d

    spiders_in_range = [s for s in spiders if s.threat_for != 2]
    for s in spiders_in_range:
        if (s.threat_for == 1 or hypot(base_x + 2000 * d - s.x - s.vx,
                                       base_y + 4500 * d - s.y - s.vy) < 3500) and hypot(target_x - s.x,
                                                                                         target_y - s.y) > 2700 and hypot(
                hero.x - s.x, hero.y - s.y) < 1280:
            return True
    return False


def drag(hero):
    d = direction()
    target_x = base_x + 4200 * d
    target_y = base_y + 8500 * d
    print(f'SPELL WIND {target_x} {target_y}')
    return NodeStatus.SUCCESS


def should_control_spider(hero):
    if not (have_enough_mana() and have_mana()):
        return False
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x,
                                                    hero.y - s.y) < 2200 and s.health > 12 and s.threat_for != 2 and s.id not in claimed_entities and not s.shield_life]
    if len(spiders_in_range) > 0:
        return True
    return False


def control_spider(hero):
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x,
                                                    hero.y - s.y) < 2200 and s.health > 12 and s.threat_for != 2 and s.id not in claimed_entities and not s.shield_life]
    if not spiders_in_range:
        return NodeStatus.FAILURE
    spiders_in_range.sort(key=lambda spider: -spider.health)
    spider = spiders_in_range[0]
    print(f'SPELL CONTROL {spider.id} {opp_base_x} {opp_base_y}')
    claimed_entities.add(spider.id)
    return NodeStatus.SUCCESS


def should_escort(hero):
    if not (have_enough_mana() and have_mana()):
        return False
    spiders_in_range = [s for s in spiders if s.threat_for == 2]
    if hypot(opp_base_x - hero.x, opp_base_y - hero.y) < 2500:
        return False
    if len(spiders_in_range) > 1:
        return True
    return False


def escort(hero):
    d = direction()
    spiders_in_range = [s for s in spiders if s.threat_for == 2]
    spiders_in_range.sort(key=lambda s: hypot(opp_base_x - s.x, opp_base_y - s.y))
    spider_xs = [s.x for s in spiders_in_range[:2]]
    spider_ys = [s.y for s in spiders_in_range[:2]]
    target_x = int(np.mean(spider_xs)) + random.randint(2000, 2800) * d
    target_y = int(np.mean(spider_ys)) - random.randint(800, 1000) * d

    for s in spiders:
        while hypot(target_x - s.x, target_y - s.y) < 1500:
            target_x += random.randint(-400, 400) * d
            target_y -= random.randint(-200, 200) * d

    print(f'MOVE {target_x} {target_y}')
    return NodeStatus.SUCCESS


def should_control_opp(hero):
    if not (have_enough_mana() and have_mana() and spiders):
        return False
    opp_in_range = [o for o in opp_heros if hypot(hero.x - o.x,
                                                  hero.y - o.y) < 2200 * 1 and o.id not in claimed_entities and not o.shield_life and hypot(
        opp_base_x - o.x, opp_base_y - o.y) < 8000]
    if len(opp_in_range) > 0:
        return True
    return False


def control_opp(hero):
    opp_in_range = [o for o in opp_heros if hypot(hero.x - o.x,
                                                  hero.y - o.y) < 2200 * 1 and o.id not in claimed_entities and not o.shield_life and hypot(
        opp_base_x - o.x, opp_base_y - o.y) < 8000]
    nearest_spider = sorted(spiders, key=lambda s: hypot(opp_base_x - s.x, opp_base_y - s.y))[0]
    opp_in_range.sort(key=lambda o: hypot(o.x - nearest_spider.x, o.y - nearest_spider.y))
    opp = opp_in_range[0]
    d = direction()
    print(f'SPELL CONTROL {opp.id} {opp_base_x - 10000 * d} {opp_base_y - 15000 * d}')
    claimed_entities.add(opp.id)
    return NodeStatus.SUCCESS


def should_wind_spider(hero):
    if not (have_enough_mana() and have_mana()):
        return False
    spiders_in_range = [s for s in spiders if
                        hypot(s.x - hero.x, s.y - hero.y) < 1280 and s.threat_for == 2 and not s.shield_life]
    if hypot(hero.x - opp_base_x, hero.y - opp_base_y) < 7500 and len(spiders_in_range) > 1:
        return True
    return False


def wind_spider(hero):
    d = direction()
    spiders_in_range = [s for s in spiders if
                        hypot(s.x - hero.x, s.y - hero.y) < 1280 and s.threat_for == 2 and not s.shield_life]
    if len(spiders_in_range) > 1:
        spider_xs = [s.x for s in spiders_in_range]
        spider_ys = [s.y for s in spiders_in_range]
        s_x = int(np.mean(spider_xs))
        s_y = int(np.mean(spider_ys))

        print(f'SPELL WIND {opp_base_x - s_x + hero.x} {opp_base_y - s_y + hero.y}')
    else:
        print(f'SPELL WIND {opp_base_x} {opp_base_y}')
    return NodeStatus.SUCCESS


def should_shield_spider(hero):
    if not (have_enough_mana() and have_mana()):
        return False
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x,
                                                    hero.y - s.y) < 2200 and s.threat_for == 2 and s.id not in claimed_entities and not s.shield_life]
    if len(spiders_in_range) < 1:
        return False
    spiders_in_range.sort(key=lambda s: (-s.health, hypot(s.x - opp_base_x, s.y - opp_base_y)))
    spider = spiders_in_range[0]
    if hypot(spider.x - opp_base_x, spider.y - opp_base_y) < 4500 and spider.health > 8:
        return True
    return False


def shield_spider(hero):
    spiders_in_range = [s for s in spiders if hypot(hero.x - s.x,
                                                    hero.y - s.y) < 2200 and s.threat_for == 2 and s.id not in claimed_entities and not s.shield_life]
    spiders_in_range.sort(key=lambda s: (-s.health, hypot(s.x - opp_base_x, s.y - opp_base_y)))
    spider = spiders_in_range[0]
    print(f'SPELL SHIELD {spider.id}')
    claimed_entities.add(spider.id)
    return NodeStatus.SUCCESS


def build_attacker_tree():
    root = Selector("Root")

    control_seq = Sequence('control_spiders')
    control_seq.add_child(Condition('should_control_spider', should_control_spider))
    control_seq.add_child(Action('control_spider', control_spider))

    escort_seq = Sequence('escort')
    escort_seq.add_child(Condition('should_escort', should_escort))
    escort_seq.add_child(Action('escort', escort))

    control_opp_seq = Sequence('control_opp')
    control_opp_seq.add_child(Condition('should_control_opp', should_control_opp))
    control_opp_seq.add_child(Action('control_opp', control_opp))

    wind_seq = Sequence('wind_seq')
    wind_seq.add_child(Condition('should_wind_spider', should_wind_spider))
    wind_seq.add_child(Action('wind_spider', wind_spider))

    shield_seq = Sequence('shield_seq')
    shield_seq.add_child(Condition('should_shield_spider', should_shield_spider))
    shield_seq.add_child(Action('shield_spider', shield_spider))

    drag_seq = Sequence('drag_seq')
    drag_seq.add_child(Condition('should_drag', should_drag))
    drag_seq.add_child(Action('drag', drag))

    gather_seq = Sequence('gather_seq')
    gather_seq.add_child(Condition('should_gather', should_gather))
    gather_seq.add_child(Action('gather', gather))
    # 最低优先级: 巡逻
    patrol_act = Action("Farm", farm)

    root.add_child(wind_seq)
    root.add_child(shield_seq)
    root.add_child(control_opp_seq)
    root.add_child(control_seq)
    root.add_child(escort_seq)

    #    root.add_child(gather_seq)
    root.add_child(drag_seq)
    root.add_child(patrol_act)

    return root


# Data
@dataclass
class Spider():
    id: int
    x: int
    y: int
    vx: int
    vy: int
    health: int
    near_base: bool
    threat_for: bool
    shield_life: int = 0
    is_controlled: int = 0


@dataclass
class Hero():
    id: int
    x: int
    y: int
    shield_life: int = 0
    is_controlled: int = 0
    last_x: int = 0
    last_y: int = 0


# base_x: The corner of the map representing your base
base_x, base_y = [int(i) for i in input().split()]
heroes_per_player = int(input())  # Always 3
opp_base_x = 17630 - base_x
opp_base_y = 9000 - base_y

# 使用示例
defender_tree = build_defender_tree()
attacker_tree1 = build_attacker_tree()
attacker_tree2 = build_attacker_tree()

my_mana_history = []
claimed_entities = set()

# game loop
while True:
    spiders = []
    my_heros = []
    opp_heros = []

    my_health, my_mana = [int(j) for j in input().split()]
    opp_health, opp_mana = [int(j) for j in input().split()]
    my_mana_history.append(my_mana)

    entity_count = int(input())  # Amount of heros and monsters you can see
    for i in range(entity_count):
        # _id: Unique identifier
        # _type: 0=monster, 1=your hero, 2=opponent hero
        # x: Position of this entity
        # shield_life: Ignore for this league; Count down until shield spell fades
        # is_controlled: Ignore for this league; Equals 1 when this entity is under a control spell
        # health: Remaining health of this monster
        # vx: Trajectory of this monster
        # near_base: 0=monster with no target yet, 1=monster targeting a base
        # threat_for: Given this monster's trajectory, is it a threat to 1=your base, 2=your opponent's base, 0=neither
        _id, _type, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = [int(j) for j in
                                                                                               input().split()]
        if _type == 0:
            spiders.append(Spider(_id, x, y, vx, vy, health, near_base, threat_for, shield_life, is_controlled))
        elif _type == 1:
            my_heros.append(Hero(_id, x, y, shield_life, is_controlled))
        elif _type == 2:
            opp_heros.append(Hero(_id, x, y, shield_life, is_controlled))

    print(spiders, file=sys.stderr, flush=True)

    d = direction()
    my_heros.sort(key=lambda h: h.id)

    defender_tree.reset()

    for i, hero in enumerate(my_heros):
        print(hero.id, file=sys.stderr, flush=True)
        if i == 1:
            defender_tree.execute(hero)
        elif i == 0:
            attacker_tree1.execute(hero)
        else:
            attacker_tree2.execute(hero)

    claimed_entities.clear()
    if my_mana < 20 and have_enough_mana():
        my_mana_history = [-1]

    for h in opp_heros:
        h.last_x = h.x
        h.last_y = h.y
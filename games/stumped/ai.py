# This is where you build your AI for the Stumped game.

from joueur.base_ai import BaseAI
from math import floor, ceil
import random
import heapq
from collections import defaultdict

WATER = 'water'
LAND = 'land'
NORTH = 'North'
SOUTH = 'South'
EAST = 'East'
WEST = 'West'
FOOD = 'food'
BRANCHES = 'branches'

def get_adjacent(tile, direction):
    if direction == NORTH:
        return tile.tile_north
    elif direction == SOUTH:
        return tile.tile_south
    elif direction == EAST:
        return tile.tile_east
    elif direction == WEST:
        return tile.tile_west
    else:
        raise Exception("Unknown direction: " + direction)

def opposite(direction):
    if direction == NORTH:
        return SOUTH;
    elif direction == SOUTH:
        return NORTH
    elif direction == EAST:
        return WEST
    elif direction == WEST:
        return EAST
    else:
        raise Exception("Unknown direction: " + direction)


def tile_distance(t1, t2):
    return abs(t1.x - t2.x) + abs(t1.y - t2.y)

def can_act(beaver):
    return beaver and beaver.turns_distracted == 0 and beaver.health > 0 and not try_suicide(beaver)

def try_suicide(beaver):
    """If you are fully trapped and you're already on a lodge, just give up."""
    for neighbor in beaver.tile.get_neighbors():
        if not neighbor._spawner and not neighbor._lodge_owner:
            return False
    if not beaver.tile.lodge_owner:
        return False
    return True

def permablocked(tile):
    """If all neighbors are immovable, impathable objects"""
    for neighbor in tile.get_neighbors():
        if not neighbor._spawner and not neighbor._lodge_owner:
            return False
    return True

def move_cost(start, end):
    if start.type == WATER:
        # Going with the flow
        if start.flow_direction and get_adjacent(start, start.flow_direction) is end:
            return 1
        elif end.flow_direction and get_adjacent(end, end.flow_direction) is start:
            return 3
        else:
            return 2
    elif start.type == LAND:
        return 2
    else:
        raise Exception("Unknown tile type:", start.type)

def pathable(tile):
    return tile and tile.is_pathable()

def droppable(tile):
    return tile and not tile.spawner and not tile.flow_direction

def load(beaver):
    return beaver.branches + beaver.food

class AI(BaseAI):
    """ The basic AI functions that are the same between games. """

    def get_name(self):
        """ This is the name you send to the server so your AI will control the player named this string.

        Returns
            str: The name of your Player.
        """
        return "the-goldman-clause"

    def start(self):
        """ This is called once the game starts and your AI knows its playerID and game. You can initialize your AI here.
        """
        # replace with your start logic

    def game_updated(self):
        """ This is called every time the game's state updates, so if you are tracking anything you can update it here.
        """
        # replace with your game updated logic

    def end(self, won, reason):
        """ This is called when the game ends, you can clean up your data and dump files here if need be.

        Args:
            won (bool): True means you won, False means you lost.
            reason (str): The human readable string explaining why you won or lost.
        """
        # replace with your end logic

    def my_lodge(self, tile):
        return tile.lodge_owner and tile.lodge_owner == self.player

    def their_lodge(self, tile):
        return tile.lodge_owner and tile.lodge_owner == self.player.opponent

    def spawn(self):
        """
        Perform spawn action. Prioritizes lodge closest to a branch spawner.
        Tries to keep an even number of Builders and Fighters, ties going to Builders.
        """
        can_spawn = {lodge for lodge in self.player.lodges if not lodge.beaver and not permablocked(lodge)}
        enemies = [beaver.tile for beaver in self.player.opponent.beavers]
        while self.alive_beavers < self.game.free_beavers_count:
            path = []
            if self.num_builders > self.num_fighters and enemies:
                job = self.FIGHTER
                self.num_fighters += 1
                path = self.find_path(can_spawn, enemies)
            if not path:
                job = self.BUILDER
                self.num_builders += 1
                path = self.find_path(can_spawn, self.branch_spawners())
            if not path:
                break
            lodge = path[0]
            can_spawn.remove(lodge)
            job.recruit(lodge)
            self.alive_beavers += 1

    def enough_to_build(self, beaver, tile):
        return beaver.branches + tile.branches >= self.player.branches_to_build_lodge

    def try_build_lodge(self, beaver):
        if not can_act(beaver) or beaver.actions == 0:
            return
        if self.enough_to_build(beaver, beaver.tile) and not beaver.tile.lodge_owner:
            beaver.build_lodge()

    def try_pickup_opponent(self, beaver):
        """Attempt to take branches from opponent lodges, prioritizing the lowest health lodge."""
        if not can_act(beaver) or beaver.actions == 0 or load(beaver) >= beaver.job.carry_limit:
            return
        neighbors = beaver.tile.get_neighbors()
        branch_tiles = [tile for tile in neighbors if tile.branches > 0 and self.their_lodge(tile)]
        if branch_tiles:
            tile = min(branch_tiles, key=lambda tile: tile.branches)
            beaver.pickup(tile, 'branches', min(tile.branches, beaver.job.carry_limit - load(beaver)))

    def try_harvest(self, beaver, type):
        """Attempt harvest from a branch spawner, prioritizing the highest health spawner."""
        if not can_act(beaver) or beaver.actions == 0 or load(beaver) >= beaver.job.carry_limit:
            return
        harvest_tiles = [tile for tile in beaver.tile.get_neighbors()
                         if tile.spawner and tile.spawner.health > 1 and tile.spawner.type == type]
        if harvest_tiles:
            tile = max(harvest_tiles, key=lambda tile: tile.spawner.health)
            beaver.harvest(tile.spawner)

    def try_attack(self, beaver):
        """
        Always try to steal branches from the opponents lodge first,
        but then try to attack the lowest health opponent in range.
        Ignore distracted beavers.
        """
        self.try_pickup_opponent(beaver)
        if not can_act(beaver) or beaver.actions == 0:
            return

        target_tiles = [tile for tile in beaver.tile.get_neighbors()
                        if tile.beaver and tile.beaver.owner != self.player and
                        tile.beaver.recruited and tile.beaver.health > 0 and beaver.turns_distracted == 0]
        if target_tiles:
            target_tile = min(target_tiles, key=lambda tile: tile.beaver.health)
            beaver.attack(target_tile.beaver)

    def attack_move(self, beaver, path, last_step):
        """
        Makes sure you try attack at every step along the path.
        If last_step is False, don't try to move to the final tile in the path.
        Assumes the first step in the path is the beaver's current location.
        """
        self.try_attack(beaver)
        for step in path[1:]:
            if move_cost(beaver.tile, step) > beaver.moves:
                break
            if step is path[-1] and not last_step:
                break
            beaver.move(step)
            self.try_attack(beaver)

    def try_move_off_lodge(self, beaver):
        """
        If you're on a lodge, and one of your neighbors isn't a lodge, move off.
        Prioritize closer to branch spawners.
        """
        if not can_act(beaver) or not beaver.tile.lodge_owner:
            return
        non_lodge_tiles = [tile for tile in beaver.tile.get_neighbors() if pathable(tile)]
        if non_lodge_tiles:
            path = self.find_path(non_lodge_tiles, self.branch_spawners())
            if path:
                step = path[0]
                if move_cost(beaver.tile, step) <= beaver.moves:
                    beaver.move(step)

    def branch_spawners(self):
        return {tile for tile in self.game.tiles
                if tile.spawner and tile.spawner.health > 1 and tile.spawner.type == BRANCHES}

    def gather_branches(self, beaver):
        """Full turn command that tries to move to the nearest branch spawner and get branches."""
        self.try_attack(beaver)
        self.try_harvest(beaver, BRANCHES)
        goals = [tile for tile in self.game.tiles
                 if tile.spawner and tile.spawner.health > 1 and tile.spawner.type == BRANCHES]
        path = self.find_path([beaver.tile], goals)
        self.attack_move(beaver, path, last_step=False)
        self.try_harvest(beaver, BRANCHES)

    def pile_branches(self, beaver):
        """
        Full turn command that tries to drop off branches intelligently.
        If there is a near by pile, move and add to it, otherwise just dump next to you.
        """
        self.try_attack(beaver)
        goals = [tile for tile in self.closer_to_me
                 if droppable(tile) and not self.my_lodge(tile) and not self.their_lodge(tile)]
        path = self.find_path([beaver.tile], goals)
        better = [tile for tile in goals if tile.branches > 0]
        if better:
            better_path = self.find_path([beaver.tile], better)
            if better_path:
                turns_away = len(better_path) - len(path)
                more_needed = self.player.branches_to_build_lodge - beaver.branches - path[-1].branches
                if more_needed / beaver.job.carry_limit > turns_away:
                    path = better_path
        if not path:
            return
        if self.enough_to_build(beaver, path[-1]):
            self.attack_move(beaver, path, last_step=True)
            self.try_build_lodge(beaver)
        else:
            self.attack_move(beaver, path, last_step=False)
            if len(path) > 1 and tile_distance(beaver.tile, path[-1]) < 2:
                if beaver.actions > 0 and beaver.branches > 0:
                    beaver.drop(path[-1], 'branches', beaver.branches)

    def go_hunting(self, beaver):
        """Full turn command to seek out and attack enemy lodges."""
        self.try_attack(beaver)
        path = self.find_path([beaver.tile], [tile for tile in self.game.tiles if self.their_lodge(tile)])
        if not path:
            path = self.find_path([beaver.tile], [enemy.tile for enemy in self.player.opponent.beavers
                                                  if enemy.health > 0 and enemy.turns_distracted == 0])
        self.attack_move(beaver, path, last_step=False)

    def setup(self):
        for job in self.game.jobs:
            if job.title == 'Hungry':
                self.HUNGRY = job
            elif job.title == 'Fighter':
                self.FIGHTER = job
            elif job.title == 'Basic':
                self.BASIC = job
            elif job.title == 'Bulky':
                self.BULKY = job
            elif job.title == 'Swift':
                self.SWIFT = job
            elif job.title == 'Hot Lady':
                self.HOT_LADY = job
            elif job.title == 'Builder':
                self.BUILDER = job
            else:
                raise Exception("Bad job title:" + job.title)
        self.COMBAT = set([self.HUNGRY, self.BASIC, self.HOT_LADY, self.FIGHTER])
        self.alive_beavers = len([beaver for beaver in self.player.beavers if beaver.health > 0])
        self.num_fighters = len([beaver for beaver in self.player.beavers if beaver.job is self.FIGHTER])
        self.num_builders = len([beaver for beaver in self.player.beavers if beaver.job is self.BUILDER])

    def run_turn(self):
        """ This is called every time it is this AI.player's turn.

        Returns:
            bool: Represents if you want to end your turn. True means end your turn, False means to keep your turn going and re-call this function.
        """
        print('My Turn {}'.format(self.game.current_turn))
        self.setup()
        self.set_nearest_beaver()
        self.spawn()
        for beaver in self.player.beavers:
            if not can_act(beaver):
                continue
            # Always try to build a lodge if you can
            self.try_build_lodge(beaver)
            if load(beaver) >= beaver.job.carry_limit:
                if beaver.job in self.COMBAT:
                    # Combat beavers don't have time for smart piling,
                    # they just dump stuff.
                    self.try_build_lodge(beaver)
                    beaver.drop(beaver.tile, BRANCHES, beaver.branches)
                else:
                    self.try_build_lodge(beaver)
                    self.pile_branches(beaver)
            elif beaver.job in self.COMBAT:
                self.go_hunting(beaver)
            else:
                self.gather_branches(beaver)
        for beaver in self.player.beavers:
            # If you still have moves left, try not to end your turn
            # on a lodge
            self.try_move_off_lodge(beaver)
        # Calls spawn a second time just in case some lodges have freed up.
        self.spawn()
        print('Done with our turn')
        return True  # to signify that we are truly done with this turn

    def find_path(self, start_tiles, goal_tiles):
        """
        Given a list of starting locations and a list of ending locations,
        find the shortest path between them. Uses a priority queue to
        do Uniform Cost Search (think Breadth First Search, but with movement
        cost included).
        """
        open_q = [(0, tile) for tile in start_tiles]
        heapq.heapify(open_q)
        goals = {tile for tile in goal_tiles}
        source = defaultdict(lambda: (None, 100000000))
        for tile in start_tiles:
            source[tile] = (tile, 0)
        while open_q:
            moves, working = heapq.heappop(open_q)
            for neighbor in working.get_neighbors():
                if neighbor in goals:
                    steps = [neighbor, working]
                    previous = working
                    while source[previous][0] != previous:
                        previous = source[previous][0]
                        steps.append(previous)
                    return list(reversed(steps))
                if not pathable(neighbor):
                    continue
                previous_tile, previous_distance = source[neighbor]
                current_distance = moves + move_cost(working, neighbor)
                if current_distance < previous_distance:
                    source[neighbor] = (working, current_distance)
                    heapq.heappush(open_q, (current_distance, neighbor))
        return []

    def set_nearest_beaver(self):
        """
        Builds the 'closer_to_me' set of tiles, which are all tiles that are
        distance-wise closer to my units than theirs. Pretty sure this
        wasn't useful at all.
        """
        open_q = [(0, beaver.tile, beaver) for beaver in self.game.beavers]
        heapq.heapify(open_q)
        source = defaultdict(lambda: (None, 100000000))
        for beaver in self.game.beavers:
            source[beaver.tile] = (beaver, 0)
        while open_q:
            moves, working, beaver = heapq.heappop(open_q)
            for neighbor in working.get_neighbors():
                previous_beaver, previous_distance = source[neighbor]
                current_distance = moves + move_cost(working, neighbor)
                if previous_beaver is None or ceil(current_distance / beaver.job.moves) < ceil(previous_distance / previous_beaver.job.moves):
                    source[neighbor] = (beaver, current_distance)
                    if pathable(neighbor):
                        heapq.heappush(open_q, (current_distance, neighbor, beaver))
        self.closer_to_me = set()
        self.closer_to_them = set()
        for tile in self.game.tiles:
            beaver, _ = source[tile]
            if not beaver:
                continue
            if beaver.owner == self.player:
                self.closer_to_me.add(tile)
            else:
                self.closer_to_them.add(tile)

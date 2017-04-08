# This is where you build your AI for the Stumped game.

from joueur.base_ai import BaseAI
from math import floor, ceil
import random
import heapq
from collections import defaultdict

WATER = 'Water'
LAND = 'Land'
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
    

def can_act(beaver):
    return beaver and beaver.turns_distracted == 0 and beaver.health > 0

def move_cost(start, end):
    if start.type == WATER:
        # Going with the flow
        if get_adjacet(start, start.flow_direction) is end:
            return 1
        elif get_adjacent(tile, opposite(direction)) is end:
            return 3
    return 2

def pathable(tile):
    return tile and tile.is_pathable()

def load(beaver):
    return beaver.branches + beaver.food

class AI(BaseAI):
    """ The basic AI functions that are the same between games. """

    def get_name(self):
        """ This is the name you send to the server so your AI will control the player named this string.

        Returns
            str: The name of your Player.
        """
        return "the-goldman-clause"  # REPLACE THIS WITH YOUR TEAM NAME

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

    def spawn(self):
        can_spawn = [lodge for lodge in self.player.lodges if not lodge.beaver]
        alive_beavers = len([beaver for beaver in self.player.beavers if beaver.health > 0])
        for lodge in self.player.lodges:
            if lodge.beaver:
                continue
            # and we need a Job to spawn
            job = random.choice(self.game.jobs)

            # if we have less beavers than the freeBeavers count, it is free to spawn
            #    otherwise if that lodge has enough food on it to cover the job's cost
            if alive_beavers < self.game.free_beavers_count or lodge.food >= job.cost:
                # then spawn a new beaver of that job!
                print('Recruiting {} to {}'.format(job, lodge))
                job.recruit(lodge)
                alive_beavers += 1

    def try_build_lodge(self, beaver):
        if not can_act(beaver) or beaver.actions == 0:
            return
        if (beaver.branches + beaver.tile.branches) >= self.player.branches_to_build_lodge and not beaver.tile.lodge_owner:
            print('{} building lodge'.format(beaver))
            beaver.build_lodge()

    def try_pick_up(self, beaver):
        if not can_act(beaver) or beaver.actions == 0 or load(beaver) >= beaver.job.carry_limit:
            return
        neighbors = beaver.tile.get_neighbors()
        neighbors.append(beaver.tile)
        branch_tiles = [tile for tile in neighbors if tile.branches > 0 and not self.my_lodge(tile)]
        if branch_tiles:
            tile = random.choice(branch_tiles)
            print('{} picking up branches'.format(beaver))
            beaver.pickup(tile, 'branches', 1)
#         # try to pickup food
#         elif tile.food > 0:
#             print('{} picking up food'.format(beaver))
#             beaver.pickup(tile, 'food', 1)
#             break

    def try_harvest(self, beaver):
        # if we can carry more, try to harvest something
        if not can_act(beaver) or beaver.actions == 0 or load(beaver) >= beaver.job.carry_limit:
            return
        harvest_tiles = [tile for tile in beaver.tile.get_neighbors() if tile.spawner]
        if harvest_tiles:
            tile = random.choice(harvest_tiles)
            print('{} harvesting {}'.format(beaver, tile.spawner))
            beaver.harvest(tile.spawner)

    def try_attack(self, beaver):
        if not can_act(beaver) or beaver.actions == 0:
            return
        target_tiles = [tile for tile in beaver.tile.get_neighbors() if tile.beaver and tile.beaver.owner != self.player]
        if target_tiles:
            target_tile = random.choice(target_tiles)
            print('{} attacking {}'.format(beaver, target_tile.beaver))
            beaver.attack(target_tile.beaver)

    def run_turn(self):
        """ This is called every time it is this AI.player's turn.

        Returns:
            bool: Represents if you want to end your turn. True means end your turn, False means to keep your turn going and re-call this function.
        """
        # This is your Stumped ShellAI
        # ShellAI is intended to be a simple AI that does everything possible in the game, but plays the game very poorly
        # This example code does the following:
        # 1. Grabs a single beaver
        # 2. tries to move the beaver
        # 3. tries to do one of the 5 actions on it
        # 4. Grabs a lodge and tries to recruit a new beaver

        # First let's do a simple print statement telling us what turn we are on
        print('My Turn {}'.format(self.game.current_turn))
        self.spawn()
        # 1. get the first beaver to try to do things with
        for beaver in self.player.beavers:  # if we have a beaver, and it's not distracted, and it is alive (health greater than 0)
            if not can_act(beaver):
                continue
            self.try_attack(beaver)
            self.try_build_lodge(beaver)
            self.try_harvest(beaver)
            self.try_pick_up(beaver)
            goals = [tile for tile in self.game.tiles if tile.spawner and tile.spawner.health > 1 and tile.spawner.type == BRANCHES]
            if load(beaver) >= beaver.job.carry_limit:
                goals = [tile for tile in self.game.tiles if self.my_lodge(tile)]
            if goals:
                path = self.find_path([beaver.tile], goals)
                for step in path[1:-1]:
                    if move_cost(beaver.tile, step) <= beaver.moves:
                        print('Moving {} towards {}'.format(beaver, path[-1]))
                        beaver.move(step)
            self.try_attack(beaver)
            self.try_build_lodge(beaver)
            self.try_pick_up(beaver)
            self.try_harvest(beaver)
            
            # 3. Try to do an action on the beaver
            if beaver.actions > 0:
                # then let's try to do an action!

                if False:
                    # choose a random tile from our neighbors + out tile to drop stuff on
                    neighbors = beaver.tile.get_neighbors()
                    neighbors.append(beaver.tile)
                    drop_tiles = neighbors

                    # find a valid tile to drop resources onto
                    tile_to_drop_on = None
                    for tile in drop_tiles:
                        if not tile.spawner:
                            tile_to_drop_on = tile
                            break

                    # if there is a tile that resources can be dropped on
                    if tile_to_drop_on:
                        # if we have branches to drop
                        if beaver.branches > 0:
                            print('{} dropping 1 branch'.format(beaver))
                            beaver.drop(tile_to_drop_on, 'branches', 1)
                        # or if we have food to drop
                        elif beaver.food > 0:
                            print('{} dropping 1 food'.format(beaver))
                            beaver.drop(tile_to_drop_on, 'food', 1)

        print('Done with our turn')
        return True # to signify that we are truly done with this turn

    def find_path(self, start_tiles, goal_tiles):
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

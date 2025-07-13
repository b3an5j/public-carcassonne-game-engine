# from helper.game import *
from lib.config.map_config import MAP_CENTER, MAX_MAP_LENGTH, MONASTARY_IDENTIFIER
from lib.interact.tile import create_base_tiles, create_river_tiles, Tile
from lib.interact.structure import StructureType
from itertools import product


# CARDS
class EdgeLayer:
    def __init__(self, orientation: str, stc_list):
        self.orientation = orientation
        self.structs = {s: None for s in stc_list}


class Deck:
    @staticmethod
    def _generate_slots(depth: int, ori_list: list[str], stc_list: list[dict], deck=None):
        """Generate slots for cards to form a deck"""
        # base case
        if depth == 1:
            return
        
        # recursive case
        if not deck:
            deck = EdgeLayer(ori_list[depth-1], stc_list)
        for s in deck.structs:
            deck.structs[s] = EdgeLayer(ori_list[depth-2], stc_list)
            Deck._generate_slots(depth-1, ori_list, stc_list, deck.structs[s])
        return deck

    def __init__(self):
        self.ori = Tile.get_edges()
        self.stc = [
            StructureType.RIVER,
            StructureType.ROAD,
            StructureType.ROAD_START,
            StructureType.CITY,
            StructureType.GRASS
        ]
        self.cards = Deck._generate_slots(len(self.ori), self.ori, self.stc)
        self.in_hand = None
    
    def _fetch_leaf(self, tile: Tile, check_last=False) -> EdgeLayer | Tile:
        """
        Fetch the last layer of deck that might contain the card.
        If check_last is enabled, check the last edge and returns that card instead.
        """
        temp = self.cards
        try:
            for _ in range(len(self.ori)-1):
                temp= temp.structs[tile.internal_edges[temp.orientation]]
        except KeyError:
            return None
        
        # previous layers matched, check for the last
        if check_last:
            for s in temp.structs:
                try:
                    if s == tile.internal_edges[temp.orientation]:
                        return temp.structs[s][0]
                except KeyError:
                    continue
            return None
        
        return temp
    
    def _reset_rotation(self, tile: Tile):
        tile.rotate_clockwise(4 - tile.rotation)

    def insert_card(self, tile: Tile, num_tiles: int):
        """Insert card and number of cards into appropriate slots"""
        layer = self._fetch_leaf(tile)
        layer.structs[tile.internal_edges[layer.orientation]] = [tile, num_tiles]
    
    def remove_card(self, tile: Tile):
        """Remove card from deck"""
        # reset to original tile
        if tile.rotation:
            self._reset_rotation(tile)
        
        layer = self._fetch_leaf(tile)
        layer.structs[tile.internal_edges[layer.orientation]][1] -= 1
        
        if not layer.structs[tile.internal_edges[layer.orientation]][1]:
            layer.structs[tile.internal_edges[layer.orientation]] = None
            self.clean(self.cards, len(self.ori))

    def _load(self):
        """Load every card into the deck"""
        tiles = create_base_tiles()
        tiles.extend(create_river_tiles())
        tiles.append(Tile.get_river_end_tile())
        tiles.append(Tile.get_starting_tile())

        # count then insert tiles into deck
        count = 0
        while tiles:
            temp_last = tiles.pop()
            try:
                temp_before_last = tiles.pop()
            except IndexError:
                self.insert_card(temp_last, count)
                continue

            if not count:
                count += 1
            
            # different, insert
            if temp_last.__dict__ != temp_before_last.__dict__:
                self.insert_card(temp_last, count)
                
                # reset count
                tiles.append(temp_before_last)
                count = 0
                continue
            
            # same, keep counting
            tiles.append(temp_before_last)
            count += 1
    
    def clean(self, deck: EdgeLayer, depth: int):
        """Remove redundant children"""
        to_delete = []      # to be safe
        for stc in deck.structs:
            if deck.structs[stc] is None:
                to_delete.append(stc)    
            
            # Recursive base
            elif depth != 1:
                if self.clean(deck.structs[stc], depth-1) is None:
                    to_delete.append(stc)
        
        # Delete None(s)
        if len(to_delete) == len(deck.structs):
            deck.structs = None
        else:
            for stc in to_delete:
                del deck.structs[stc]
        
        return deck.structs
    
    def generate_deck(self):
        """Generate ready-to-use deck"""
        self._load()
        self.clean(self.cards, len(self.ori))
        return self
    
    def _possible_combinations(self, param_list: list[StructureType | None]):
        for i in range(len(param_list)):
            if not param_list[i]:
                param_list[i] = self.stc
            else:
                param_list[i] = [param_list[i]]
        combs = list(product(*param_list))

        tile_combs = []
        for c in combs:
            tile_combs.append(
                Tile(
                    "",
                    left_edge=c[0],
                    right_edge=c[1],
                    top_edge=c[2],
                    bottom_edge=c[3]
                )
            )
        return tile_combs
    
    def possible_matches(self, left_edge: StructureType=None, right_edge: StructureType=None, top_edge: StructureType=None, bottom_edge: StructureType=None):
        """Search for possible matches in current deck of cards"""
        # empty params
        if left_edge is right_edge is top_edge is bottom_edge is None:
            print("MUST SPECIFY AT LEAST ONE")
            return []
        
        matched_tiles = []
        possible_tiles: list[Tile] = self._possible_combinations([left_edge, right_edge, top_edge, bottom_edge])
        for t in possible_tiles:
            # rotate 4 times to check
            for _ in range(4):
                t.rotate_clockwise(1)
                matched = self._fetch_leaf(t, check_last=True)
                if matched and matched not in matched_tiles:
                    matched_tiles.append(matched)
        return matched_tiles

# BOARD
class Board:
    def __init__(self):
        self.grid = {}
        for i in range(MAX_MAP_LENGTH):
            for j in range(MAX_MAP_LENGTH):
                self.grid[(i, j)] = None

        self.scannable = [
            [MAP_CENTER[0]-1, MAP_CENTER[1]-1],     # towards top-left corner (2nd quadrant)
            [MAP_CENTER[0]+1, MAP_CENTER[1]+1]      # towards bottom-right corner (4th quadrant)
        ]  # no need to brute force
    
    def place_tile(self, x: int, y: int, tile:Tile):
        tile.placed_pos = (x, y)
        self.grid[(x, y)] = tile

        # update scannable area
        for i in range(2):
            x_diff = x - self.scannable[i][0]
            if not x_diff:
                if i == 0:
                    self.scannable[0][0] -= 1
                    return
                else:
                    self.scannable[1][0] += 1
                    return
            y_diff = y - self.scannable[i][1]
            if not y_diff:
                if i == 0:
                    self.scannable[0][1] -= 1
                    return
                else:
                    self.scannable[1][1] += 1
                    return
        # DON'T FORGET TO REMOVE CARD FROM DECK


# BOT
class Bot:
    def __init__(self):
        # self.game = Game()
        self.deck = Deck().generate_deck()
        self.board = Board()
    
    def place_tile(self, x: int, y: int, tile:Tile):
        self.board(x, y, tile)
        self.deck.remove_card(tile)

    # def handle_place_tile(self, query: QueryPlaceTile):
    #     pass

    # def handle_place_meeple(self, query: QueryPlaceMeeple):
    #     pass
    
    # def choose_move(self, query: QueryType):
    #     match query:
    #         case QueryPlaceTile() as q:
    #                 return self.handle_place_tile(q)

    #         case QueryPlaceMeeple() as q:
    #             return self.handle_place_meeple(q)

    def run(self):
        # while True:
        #     query = self.game.get_next_query()
        #     self.game.send_move(self.choose_move(query))
        a = self.deck.possible_matches(top_edge=StructureType.GRASS, bottom_edge=StructureType.GRASS, left_edge=StructureType.CITY)
        pass


if __name__ == "__main__":
    BOT = Bot()
    BOT.run()
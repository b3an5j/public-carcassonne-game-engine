# from helper.game import *
from lib.config.map_config import MAP_CENTER, MAX_MAP_LENGTH, MONASTARY_IDENTIFIER
from lib.models.tile_model import TileModel
from lib.interact.tile import create_base_tiles, create_river_tiles, Tile, TileModifier
from lib.interact.structure import StructureType


# CARDS
class EdgeLayer:
    def __init__(self, orientation: str, stc_list):
        self.orientation = orientation
        self.structs = {s: None for s in stc_list}


class Deck:
    @staticmethod
    def generate_slots(depth: int, ori_list: list[str], stc_list: list[dict], deck=None):
        """Generate slots for cards to form a deck"""
        # base case
        if depth == 1:
            return
        
        # recursive case
        if not deck:
            deck = EdgeLayer(ori_list[depth-1], stc_list)
        for s in deck.structs:
            deck.structs[s] = EdgeLayer(ori_list[depth-2], stc_list)
            Deck.generate_slots(depth-1, ori_list, stc_list, deck.structs[s])
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
        self.cards = Deck.generate_slots(len(self.ori), self.ori, self.stc)
    
    def insert_card(self, tile: Tile, num_tiles: int):
        """Insert card and number of cards into appropriate slots"""
        temp = self.cards
        for _ in range(len(self.ori)-1):
            temp= temp.structs[tile.internal_edges[temp.orientation]]
        temp.structs[tile.internal_edges[temp.orientation]] = [tile, num_tiles]

    def load(self):
        """Load every card into the deck"""
        tiles = create_base_tiles()
        tiles.extend(create_river_tiles())
        tiles.append(Tile.get_river_end_tile())

        # count then insert tiles into deck
        count = 0
        while tiles:
            temp_last = tiles.pop()
            try:
                temp_before_last = tiles.pop()
            except IndexError:
                print(f"{temp_last}: {count}")
                self.insert_card(temp_last, count)
                continue

            if not count:
                count += 1
            
            # different, insert
            if temp_last.__dict__ != temp_before_last.__dict__:
                self.insert_card(temp_last, count)
                
                # reset
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
        self.load()
        self.clean(self.cards, len(self.ori))
        return self


# BOARD
class Board:
    def __init__(self):
        self.board = {}
        for i in range(MAX_MAP_LENGTH):
            for j in range(MAX_MAP_LENGTH):
                self.board[(i, j)] = None

        self.scannable = [
            [MAP_CENTER[0]-1, MAP_CENTER[1]-1],
            [MAP_CENTER[0]+1, MAP_CENTER[1]+1]
        ] # no need to brute force


# BOT
class Bot:
    def __init__(self):
        # self.game = Game()
        self.deck = Deck().generate_deck()
        self.board = Board()
    
    def think(query):
        pass

    def run(self):
        # while True:
        #     query = self.game.get_next_query()
        #     move = self.think(query)
        #     self.game.send_move(move)
        pass


if __name__ == "__main__":
    BOT = Bot()
    BOT.run()
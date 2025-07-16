from helper.game import *
from lib.config.map_config import MAP_CENTER, MAX_MAP_LENGTH, MONASTARY_IDENTIFIER
from lib.interact.tile import create_base_tiles, create_river_tiles, Tile
from lib.interact.structure import StructureType
from lib.interface.events.typing import *
from lib.interface.events.moves.typing import *
from itertools import product
from copy import deepcopy


# CARDS
class EdgeLayer:
    def __init__(self, orientation: str, stc_list: list[StructureType]):
        self.orientation = orientation
        self.structs = {s: None for s in stc_list}


class Deck:
    @staticmethod
    def _generate_slots(depth: int, ori_list: list[str], stc_list: list[StructureType], deck=None):
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
        self.cards = Deck._generate_slots(4, self.ori, self.stc)
    
    def copy(self):
        return deepcopy(self)
    
    def update_my_cards(self, my_tiles: list[Tile]):
        """Generate a mini deck only containing cards in hand (my_tiles)"""
        self.my_cards = Deck()
        self.my_cards.cards = EdgeLayer("", [])
        for tile in my_tiles:
            temp = self.my_cards.cards
            depth = 4
            for ori in self.ori:
                depth -= 1
                temp.orientation = ori
                stc = tile.internal_edges[ori]
                
                if stc not in temp.structs:
                    if depth:
                        temp.structs[stc] = EdgeLayer("", [])
                        temp = temp.structs[stc]
                    else:
                        temp.structs[stc] = [tile, 1]
                else:
                    if depth:
                        temp = temp.structs[stc]
                    else:
                        temp.structs[stc][1] += 1
    
    def _fetch_leaf(self, tile: Tile, check_last=False) -> EdgeLayer | Tile:
        """
        Fetch the last layer of deck that might contain the card.
        If check_last is enabled, check the last edge and returns that card instead.
        """
        temp = self.cards
        try:
            for _ in range(4-1):
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
            self.clean(self.cards, 4)

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
        self.clean(self.cards, 4)
        return self
    
    def _possible_combinations(self, param_list: list[StructureType | None]):
        """Return all combinations of Tile given edges (StructureType)"""
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

    @staticmethod
    def _symmetric(tile: Tile) -> bool:
        """Check if a tile is symmetric"""
        if tile.internal_edges["left_edge"] == tile.internal_edges["right_edge"] and tile.internal_edges["top_edge"] == tile.internal_edges["bottom_edge"]:
            return True
        return False
    
    def _possible_matches(self, left_edge: StructureType=None, right_edge: StructureType=None, top_edge: StructureType=None, bottom_edge: StructureType=None):
        """Search for possible matches in current deck of cards (rotations included inside the Tile)"""
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
                if not matched:
                    continue
                if self._symmetric(matched):
                    skip = False
                    for tile in matched_tiles:
                        if matched.tile_type == tile.tile_type:
                            skip = True
                            break
                    if skip:
                        continue
                temp = deepcopy(matched)
                temp.rotate_clockwise(4-t.rotation)
                matched_tiles.append(temp)
        return matched_tiles

# BOARD
class Board:
    def __init__(self):
        self.grid: dict[tuple[int, int]: Tile | None] = {}
        for i in range(MAX_MAP_LENGTH):
            for j in range(MAX_MAP_LENGTH):
                self.grid[(i, j)] = None

        self.placeable = {MAP_CENTER: None}  # no need to brute force
    
    def copy(self):
        return deepcopy(self)
    
    def adjacent_coords(self, pos: tuple[int, int]) -> dict[str, tuple[int, int]]:
        """Return coords of adjacent tiles"""
        return {
            "left_edge": (pos[0]-1, pos[1]),    # left tile
            "right_edge": (pos[0]+1, pos[1]),   # right_tile
            "top_edge": (pos[0], pos[1]-1),     # top_tile
            "bottom_edge": (pos[0], pos[1]+1)   # bottom_tile
        }
    
    def surrounding_edges(self, pos: tuple[int, int]=None, adjacent_tiles: dict[str, tuple[int, int]]=None):
        """Return the edges that must be matched"""
        if not adjacent_tiles:
            if not pos:
                print("MUST SPECIFY POS WHEN NOT GIVING ADJACENT TILES")
                return None
            adjacent_tiles = self.adjacent_coords(pos)
        return {
            "left_edge": self.grid[adjacent_tiles["left_edge"]].internal_edges.right_edge if self.grid[adjacent_tiles["left_edge"]] else None,
            "right_edge": self.grid[adjacent_tiles["right_edge"]].internal_edges.left_edge if self.grid[adjacent_tiles["right_edge"]] else None,
            "top_edge": self.grid[adjacent_tiles["top_edge"]].internal_edges.bottom_edge if self.grid[adjacent_tiles["top_edge"]] else None,
            "bottom_edge": self.grid[adjacent_tiles["bottom_edge"]].internal_edges.top_edge if self.grid[adjacent_tiles["bottom_edge"]] else None
        }
    
    def place_tile(self, pos: tuple[int, int], tile:Tile) -> bool:
        """
        Place a tile on the Board
        Returns True when successful
        """
        tile.placed_pos = pos

        # occupied
        if self.grid[pos]:
            return False

        self.grid[pos] = tile
        del self.placeable[pos]

        # update placeable coords
        adj_coords = self.adjacent_coords(pos)
        adj_edges = self.surrounding_edges(adjacent_tiles=adj_coords)
        for k in adj_edges:
            # take empty ones 
            if not adj_edges[k]:
                self.placeable[adj_coords[k]] = None
        # DON'T FORGET TO REMOVE CARD FROM DECK
        return True
    
    def possible_moves(self, pos: tuple[int, int], deck: Deck):
        """Search for possible moves of a coord in current deck of cards (rotations included inside the Tile)"""
        surr_edges = self.surrounding_edges(pos=pos)
        matched_tiles = deck._possible_matches(
            left_edge=surr_edges["left_edge"],
            right_edge=surr_edges["right_edge"],
            top_edge=surr_edges["top_edge"],
            bottom_edge=surr_edges["bottom_edge"]
        )
        return matched_tiles
    
    def update_my_moves(self, my_cards: list[Tile]):
        """Update possible moves depending on tiles in hand"""



# BOT
class Bot:
    def __init__(self, depth: int=5):
        # self.game = Game()
        self.deck = Deck().generate_deck()
        self.board = Board()

    def run(self):
        self.place_tile(MAP_CENTER, Tile.get_starting_tile())
        self.deck.update_my_cards([Tile.get_starting_tile(), Tile.get_starting_tile(), Tile.get_river_end_tile()])
        for e in self.all_moves().items():
            print(e)
        pass
    #     while True:
    #         query = self.game.get_next_query()
    #         print("sending move")
    #         self.game.send_move(self.choose_move(query))
    
    def place_tile(self, pos: tuple[int, int], tile:Tile):
        """Place tile on Board, then remove it from Deck"""
        self.board.place_tile(pos, tile)
        self.deck.remove_card(tile)
    
    @staticmethod
    def tile_index(tile: Tile, tile_list: list[Tile]):
        """Return index of a tile in hand"""
        for i in range(tile_list):
            if tile.tile_type == tile_list[i].tile_type:
                return i
            
    def all_moves(self):
        """Return all moves we can make"""
        moves: dict[tuple[int, int], list[Tile]] = {}
        for pos in self.board.placeable:
            temp = self.board.possible_moves(pos, self.deck.my_cards)
            if temp:
                moves[pos] = temp
        return moves
    
    def update_meeple(self, players_meeples):
        self.board.players_meeples = players_meeples

    def calculate_most_points(self) -> Tile:
        pass

    def handle_place_tile(self, query: QueryPlaceTile) -> MovePlaceTile:
        state = self.game.state
        last_moves = state.event_history[-state.new_events:]
        # Also, check the move(s) is our move so we don't do double move(s)
        
        # Update the deck
        self.deck.update_my_cards(self.game.state.my_tiles)

        # Update the board
        for event in last_moves:
            match event:
                case PublicMovePlaceTile():
                    self.place_tile(event.tile)
                    self.update_meeple(state.players_meeples)
                case EventPlayerMeepleFreed():
                    self.update_meeple(state.players_meeples)
        
        best_move = self.calculate_most_points()
        return self.game.move_place_tile(query, best_move._to_model(), Bot.tile_index(best_move))

    def handle_place_meeple(self, query: QueryPlaceMeeple) -> MovePlaceMeeple | MovePlaceMeeplePass:
        pass
    
    def choose_move(self, query: QueryType):
        match query:
            case QueryPlaceTile() as q:
                return self.handle_place_tile(q)

            case QueryPlaceMeeple() as q:
                return self.handle_place_meeple(q)
            
            case _:
                assert False


if __name__ == "__main__":
    BOT = Bot()
    BOT.run()
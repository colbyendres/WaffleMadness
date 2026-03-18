from dataclasses import dataclass
from collections import deque

@dataclass
class Node:
    team_name: str
    wh_dist: float
    
    def __repr__(self):
        return f'{self.team_name}' 
    
class Bracket:
    NUM_GAMES = 127 # Excluding First 4
    REGION_SIZE = 16 # Number of team in each region
    REGIONS = ['east', 'south', 'midwest', 'west']
    
    # Each region's starting games are orchestrated in this fashion
    # Assuming chalk, this ensures that 1v2 can only occur in finals, 1/2v3 in semifinals, etc
    SEED_ORDER = [1, 8, 5, 4, 6, 3, 7, 2]
    
    def __init__(self, bracket_dict):
        self.tree = Bracket.NUM_GAMES * [None]
        self._seed_first_round(bracket_dict)
        
    def _seed_first_round(self, bracket_dict):
        """ Seed the leaves of the tree according to the NCAA seed order """
        idx = Bracket.NUM_GAMES-64
        for region_name in Bracket.REGIONS:
            region = bracket_dict[region_name]
            for seed in Bracket.SEED_ORDER:
                lo_team, hi_team = region[seed-1], region[16 - seed]
                self.tree[idx] = Node(hi_team['name'], hi_team['distance'])
                self.tree[idx+1] = Node(lo_team['name'], lo_team['distance'])
                idx += 2
                
    
    def play(self):
        """ Simulate the tournament via post-order traversal of the tree """
        root = 0
        def traverse(self, idx):
            left, right = 2*idx+1, 2*idx+2
            if left >= Bracket.NUM_GAMES: # leaf node
                return
            traverse(self, left)
            traverse(self, right)
            if self.tree[left].wh_dist < self.tree[right].wh_dist:
                self.tree[idx] = self.tree[left]
            else:
                self.tree[idx] = self.tree[right]
        traverse(self, root)

    def get_results(self):
        """ Return the results of the tournament, starting with Round of 64 """
        root = 0
        if self.tree[root] is None:
            self.play()
            
        results = []
        queue = deque([root])
        
        while queue:
            idx = queue.popleft()
            left, right = 2*idx+1, 2*idx+2
            if left >= Bracket.NUM_GAMES:
                continue
            curr_team = self.tree[idx].team_name
            if curr_team == self.tree[left].team_name:
                results.append(f'{curr_team} def. {self.tree[right]}')
            elif curr_team == self.tree[right].team_name:
                results.append(f'{curr_team} def. {self.tree[left]}')
            else:
                raise RuntimeError(f'Team {curr_team} does not match children {self.tree[left]}, {self.tree[right]}')
            queue.extend([left, right])        

        return reversed(results) # Put Round of 64 first, then Round of 32, and so on
        
import re
import pickle

def parse(file):
    with open(file, 'r') as fp:
        buff = fp.readlines()
        matches = re.findall(r'<h2>(.+)</h2>', ''.join(buff))
        team_groups = [re.search(r'[\s\d\w\'&\(\)\.]+(?=</a>)', match) for match in matches]
    return [team.group() for team in team_groups]

file = './teams.html'
teams = parse(file)
for team in teams:
    print(team)
    
assert len(teams) == 68, f'found {len(teams)} teams'

with open('teams.txt', 'wb') as fp:
    pickle.dump(teams, fp)
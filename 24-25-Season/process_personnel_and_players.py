#!/usr/bin/env python
import csv, os, numpy

def create_team_with_coach(coach_name, c_players):
	team = {"coaches":[], "players":[], "rating":[] , "gender":[]}
	return add_coach_and_player(team, coach_name, c_players)

def find_player(coach_name):
	players_to_return = []
	for player in players:
		if (players[player]["Parent FirstName"] in coach_name and \
	  		players[player]["Parent LastName"] in coach_name) or \
			(players[player]["Secondary Contact FirstName"] in coach_name and \
			players[player]["Secondary Contact LastName"] in coach_name and \
			players[player]["Secondary Contact LastName"]!='' and \
			players[player]["Secondary Contact LastName"]!='No Answer'):
			players_to_return.append(" ".join([player[1], player[0]]))
	return players_to_return

def add_coach_and_player(team, coach_name, c_players):
	if coach_name not in team["coaches"]:
		team["coaches"].append(coach_name)
	else:
		return team
	if c_players == ["no answer"]:
		c_players = find_player(coach_name)
	for player in c_players:
		#check if player is in this division
		player_name = player.split("(")[0].strip()	
		player_fn = player_name.split()[0].lower()
		player_ln = " ".join(player_name.split()[1:]).lower()
		if player_name not in team["players"] and player_name not in added_players:
			team["players"].append(player_name)
			team["rating"].append(players[(player_ln, player_fn)]["rating"])
			team["gender"].append(players[(player_ln, player_fn)]["gender"])
			team["age"].append(players[(player_ln, player_fn)]["age"])

			added_players.append(player_name)
	return team

def add_player(team, c_player):
	player_fn = c_player[1]
	player_ln = c_player[0]
	player_name = " ".join([player_fn, player_ln])
	if player_name not in team["players"] and player_name not in added_players:
		team["players"].append(player_name)
		team["rating"].append(players[(player_ln, player_fn)]["rating"])
		team["gender"].append(players[(player_ln, player_fn)]["gender"])
		team["age"].append(players[(player_ln, player_fn)]["age"])

		added_players.append(player_name)
	return team

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('division', help="Division")
args = parser.parse_args()
DIVISION = args.division

# get previous player evals
player_ratings_file = open("2024_Player_Ratings.tsv")
player_ratings = csv.DictReader(player_ratings_file,delimiter='\t')
player_ratings_data = {}
for line in player_ratings:
	player_fn =  line['Player First'].lower()
	player_ln = line['Player Last'].lower()
	c_rating = 3
	if line['Rating']!='' and line['Rating']!= "NA - Did not play" and line['Rating']!="NA":
		c_rating = int(line['Rating'].split()[0])
	player_ratings_data[(player_ln, player_fn)] = c_rating

# get extra players
extra_players = []
if("10" in DIVISION or "12" in DIVISION):
	extra_file = open(DIVISION+"/"+DIVISION+"_Extra_Allocated.csv",encoding='latin-1')
	extra_data = csv.DictReader(extra_file,delimiter=',')
	for line in extra_data:
		player_fn = line["Player First Name"].lower()
		player_ln = line["Player Last Name"].lower()
		extra_players.append((player_ln,player_fn))
	
	# These really are *not* allocated because they were not selected after try-outs
	# extra_file = open(DIVISION+"/"+DIVISION+"_Extra_Unallocated.txt",encoding='latin-1')
	# extra_data = csv.DictReader(extra_file,delimiter='\t')
	# for line in extra_data:
	#	player_fn = line['Player Name'].split()[0].lower()
	#	player_ln = " ".join(line['Player Name'].split()[1:]).lower()
	#	extra_players.append((player_ln,player_fn))

# get current player file
player_file = open(DIVISION+"/"+DIVISION+"_Unallocated.txt",encoding='latin-1')
player_data = csv.DictReader(player_file,delimiter='\t')
players = {}
parents = {}
parents_singles = {}
experience = []
for line in player_data:
	player_fn = line['Player Name'].split()[0].lower()
	player_ln = " ".join(line['Player Name'].split()[1:]).lower()
	c_experience = line["Years of Experience:(14698163)"]
	
	# NB keep an eye on experience level as opposed to years of experience
	# print(line["Player's Experience Level(14698164)"])
	
	# NB keep an eye on payment status
	if(line['Division Price Payment Status'] != "Paid"):
		print("Warning: ",player_fn,player_ln,line['Division Price Payment Status'],line['Primary Contact Email'])

	if c_experience!="No Answer":
		experience.append(int(c_experience))

	players[(player_ln, player_fn)]= {"PlayerID": line["PlayerID"],
								   "Player FirstName": player_fn,
								   "Player LastName": player_ln,
								   "age":int(line["Age"]),
								   "gender":line["Gender"].lower(),
								   "Parent FirstName":line["Parent FirstName"].lower(),
								   "Parent LastName": line["Parent LastName"].lower(),
								   "dob":line["Date Of Birth"],
								   "Secondary Contact FirstName": line["Secondary Contact FirstName"].lower(),
								   "Secondary Contact LastName":line["Secondary Contact LastName"].lower(),
								   "Experience": c_experience}
	c_player_rating = None
	if (player_ln, player_fn) in player_ratings_data:
		c_player_rating = player_ratings_data[(player_ln, player_fn)]
	players[(player_ln, player_fn)]["rating"] = c_player_rating
	parent_tuple = (line["Parent FirstName"].lower(), \
				 	line["Parent LastName"].lower(), \
					line["Secondary Contact FirstName"].lower(), \
					line["Secondary Contact LastName"].lower())
	parent_1 = (line["Parent FirstName"].lower(), line["Parent LastName"].lower())
	parent_2 = (line["Secondary Contact FirstName"].lower(), line["Secondary Contact LastName"].lower())
	if parent_tuple not in parents:
		parents[parent_tuple]=[]
	if parent_1 not in parents_singles:
		parents_singles[parent_1] = []
	parents_singles[parent_1].append((player_ln, player_fn))
	if parent_2 not in parents_singles:	
		parents_singles[parent_2] = []
	parents_singles[parent_2].append((player_ln, player_fn))
	parents[parent_tuple].append((player_ln, player_fn))

# Get special requests
special_file = DIVISION+"/"+DIVISION+"_Pairs.txt"
special_pairs = {}
if(os.path.isfile(special_file)):
	special_file_handle = open(special_file,encoding='latin-1')
	for line in special_file_handle.readlines():
		line=line.strip('\r\n')
		(player1,player2)=line.lower().split('\t')

		player1 = player1.split()
		player1 = (" ".join(player1[1:]), player1[0])

		player2 = player2.split()
		player2 = (" ".join(player2[1:]), player2[0])

		if(player1 not in players):
			print("Missing Special Player: ",player1)
		if(player2 not in players):
			print("Missing Special Player: ",player2)

		special_pairs[player1] = player2 
		special_pairs[player2] = player1

# update players ratings based on experience?
mean_experience = sum(experience)/len(experience)
std_exp = numpy.std(experience)
coeff_var = mean_experience/std_exp
# print(DIVISION,mean_experience,std_exp)

for player in players:

	if players[player]["rating"]==None:

		if players[player]["Experience"] == 'No Answer':
			print(player,players[player]["Experience"])
			players[player]["rating"] = 3
		else:
			exp = int(players[player]["Experience"])
			adj_exp = int(exp-(coeff_var))
			players[player]["rating"] = min(3+adj_exp,5)
	
	if player in extra_players:
		players[player]["rating"] = max(4, players[player]["rating"])

if DIVISION == "5U" or DIVISION == "6U":
	average_div_rating = 0
else:
	average_div_rating = numpy.mean([players[x]["rating"] for x in players])

# get coach pairing requests and data
coach_pair_File = open(DIVISION+"/"+DIVISION+"_Coaches.tsv")
coach_pairs = csv.DictReader(coach_pair_File,delimiter='\t')
coach_pairs_data = {}
teams = {}
added_players = []
extra_teams={}
for line in coach_pairs:
	coach_first = line["First Name"].strip().lower() 
	coach_last = line["Last Name"].strip().lower()
	coach = coach_first + " " + coach_last
	team_index = line["Team"]
	if team_index == "TBD":
		continue
	player_name = []
	if (coach_first, coach_last) in parents_singles:
		player_name = parents_singles[(coach_first, coach_last)]
	else:
		print("Need to find player of -" + coach_first + "- -" + coach_last + "-")
	if team_index not in teams:
		teams[team_index] = {"coaches":[coach], "players":[], "rating":[] , "gender":[], "age":[]}
	else:
		teams[team_index]["coaches"].append(coach)
	#find and add players 
	siblings = []
	if player_name != []:
		for player in player_name:
			add_player(teams[team_index], player)
			if(DIVISION == "10UB" and player in extra_players):
				if(team_index not in extra_teams):
					extra_teams[team_index]=list()
				extra_teams[team_index].append(player)

			if player in special_pairs:
				siblings.append(special_pairs[player])
		for sibling in siblings:
			if sibling in players:
				add_player(teams[team_index], sibling)
				if(DIVISION == "10UB" and sibling in extra_players):
					if(team_index not in extra_teams):
						extra_teams[team_index]=list()
					extra_teams[team_index].append(sibling)

c_max_players = None
if DIVISION == "5U" or DIVISION == "6U":
	c_max_players = 10
if "8U" in DIVISION:
	c_max_players = 9
if "10U" in DIVISION:
	c_max_players = 10
if "12U" in DIVISION:
	c_max_players = 12
if "14UB" in DIVISION:
	c_max_players = 16
if "14UG" in DIVISION:
	c_max_players = 10

# Sort players accordingly
# Generate set of players that are above average or below average
if DIVISION == "5U" or DIVISION == "6U":
	sorted_players= sorted(players.keys(), key=lambda x: \
							(players[x]["dob"].split("/")[2], \
	   						players[x]["dob"].split("/")[0], \
							players[x]["dob"].split("/")[1]), reverse = True)
else:
	sorted_players = sorted(players.keys(), key=lambda x: players[x]["rating"], reverse = True)
c_player_index = 0
num_players = len(sorted_players)
if DIVISION == "5U" or DIVISION == "6U":
	above_average = players.keys()
	below_average = []
else:
	above_average = [player for player in players if players[player]["rating"] >= average_div_rating]
	below_average = [player for player in players if players[player]["rating"] < average_div_rating]
sorted_above = 	sorted(above_average, key=lambda x: players[x]["rating"], reverse = True)
sorted_below = 	sorted(below_average, key=lambda x: players[x]["rating"])

if(DIVISION=="10UB"):
	# Do EXTRA players first, limit to first six teams
	c_teams = list(extra_teams.keys())
	for c_player in extra_players:

		if(c_player not in players):
			#print("Warning: Extra player not registered in Core: ",c_player)
			continue

		c_teams = sorted(c_teams, key=lambda x: (\
					len(teams[x]["players"]), \
					float(sum(teams[x]['rating']))/max(len(teams[x]['rating']),1), \
					float(sum(teams[x]['age']))/max(len(teams[x]['age']),1), \
					len(teams[x]['rating']), \
					len([ g for g in teams[x]["rating"] if g == players[c_player]["rating"]])))

		siblings = 	parents[players[c_player]["Parent FirstName"].lower(), \
						 	players[c_player]["Parent LastName"].lower(), \
							players[c_player]["Secondary Contact FirstName"].lower(), \
							players[c_player]["Secondary Contact LastName"].lower()]
	
		# check for special pairings
		if c_player in special_pairs:
			siblings.append(special_pairs[c_player])
		player_added = False
		i = 0
		while not player_added and i < len(c_teams):
			if len(teams[c_teams[i]]["players"])+len(siblings) <= 6:

				c_team=  teams[c_teams[i]]
				c_team = add_player(c_team, c_player)
				player_added = True

				if(c_teams[i] not in extra_teams):
					extra_teams[c_teams[i]]=list()
				extra_teams[c_teams[i]].append(player)

				for sibling in siblings:
					if sibling in players:
						c_team = add_player(c_team, sibling)
			else:
				i+=1

#Do best players
for c_player in sorted_above:

	if(DIVISION == "10UB" and c_player in extra_players):
		continue
	
	c_teams = teams.keys()

	if DIVISION == "5U" or DIVISION == "6U":
		#process based on gender also
		c_teams = sorted(c_teams, key=lambda x: \
				   (len([ g for g in teams[x]["gender"] if g == players[c_player]["gender"]]), \
					len(teams[x]["players"])))
	else:
		c_teams = sorted(c_teams, key=lambda x: \
				   (float(sum(teams[x]['rating']))/max(len(teams[x]['rating']),1), \
					float(sum(teams[x]['age']))/max(len(teams[x]['age']),1), \
					len(teams[x]['rating']), \
					len([ g for g in teams[x]["rating"] if g == players[c_player]["rating"]])))

	siblings = 	parents[players[c_player]["Parent FirstName"].lower(), \
					 	players[c_player]["Parent LastName"].lower(), \
						players[c_player]["Secondary Contact FirstName"].lower(), \
						players[c_player]["Secondary Contact LastName"].lower()]
	# check for special pairings
	if c_player in special_pairs:
		siblings.append(special_pairs[c_player])
	player_added = False
	i = 0
	while not player_added and i < len(c_teams):
		if len(teams[c_teams[i]]["players"])+len(siblings) <= c_max_players/2:
			c_team=  teams[c_teams[i]]
			c_team = add_player(c_team, c_player)
			player_added = True
			for sibling in siblings:
				if sibling in players:
					c_team = add_player(c_team, sibling)
		else:
			i+=1

for c_player in sorted_below:

	c_teams = teams.keys()

	if DIVISION == "5U" or DIVISION == "6U":
		#process based on gender also
		c_teams = sorted(c_teams, key=lambda x: \
				   (len([ g for g in teams[x]["gender"] if g == players[c_player]["gender"]]), \
					len(teams[x]["players"])))
	else:
		c_teams = sorted(c_teams, key=lambda x: \
				   (float(sum(teams[x]['rating']))/max(len(teams[x]['rating']),1), \
					float(sum(teams[x]['age']))/max(len(teams[x]['age']),1), len(teams[x]['rating']), \
					len([ g for g in teams[x]["rating"] if g == players[c_player]["rating"]])), reverse=True)

	siblings = 	parents[players[c_player]["Parent FirstName"].lower(), \
					 	players[c_player]["Parent LastName"].lower(),\
						players[c_player]["Secondary Contact FirstName"].lower(), \
						players[c_player]["Secondary Contact LastName"].lower()]
	#check for special pairings
	if c_player in special_pairs:
		siblings.append(special_pairs[c_player])
	player_added = False
	i = 0
	while not player_added and i < len(c_teams):
		if len(teams[c_teams[i]]["players"])+len(siblings) <= c_max_players:
			c_team=  teams[c_teams[i]]
			c_team = add_player(c_team, c_player)
			player_added = True
			for sibling in siblings:
				if sibling in players:
					c_team = add_player(c_team, sibling)
		else:
			i+=1

# Missing players from selection?!
# This seems to happen with placing siblings
missing_players = [player for player in players if " ".join([player[1], player[0]]) not in added_players]

for c_player in missing_players:
	c_team = sorted(teams.keys(), key=lambda x: len(teams[x]['players']))
	siblings = 	parents[players[c_player]["Parent FirstName"].lower(), \
						players[c_player]["Parent LastName"].lower(), \
						players[c_player]["Secondary Contact FirstName"].lower(), \
						players[c_player]["Secondary Contact LastName"].lower()]
	player_added = False
	c_team=  teams[c_team[0]]
	c_team = add_player(c_team, c_player)
	player_added = True
	for sibling in siblings:
		if sibling in players:
			c_team = add_player(c_team, sibling)
missing_players = [player for player in players if " ".join([player[1], player[0]]) not in added_players]

if(len(missing_players)!=0):
	print("WARNING: UNASSIGNED PLAYERS",missing_players)

personnel_file = open(DIVISION+"/"+DIVISION+"_Personnel.txt",encoding='latin-1')
personnel_data = csv.DictReader(personnel_file,delimiter='\t')	
coach_data = {}
for line in personnel_data:
	coach_name = line["Team Personnel Name"].lower()
	coach_role = line["Team Personnel Role"]
	coach_data[coach_name]={"Team Personnel Name": coach_name, \
						 	"Team Personnel Role": coach_role, \
							"VolunteerID": line["VolunteerID"], \
							"VolunteerTypeId": line["VolunteerTypeId"]}

# output the data to upload into SportsConnect
ofh = open(DIVISION+"/"+DIVISION+"_Teams.csv",'w')
rfh = open(DIVISION+"/"+DIVISION+"_Ratings.tsv",'w')
tfh = open(DIVISION+"/"+DIVISION+"_Team_Ratings.tsv",'w')

extra_team_names = list()

output_header = ["TeamName", \
				 "PlayerID", \
				"VolunteerID", \
				"VolunteerTypeID", \
				"Player Name", \
				"Team Personnel Name", \
				"Team Personnel Role"]
ofh.write(",".join(output_header)+"\n")
team_count=0
for team in teams:
	team_count+=1
	team_name = DIVISION + " - " + format(team_count, '02d') + " - " + "/".join([coach.split()[-1] for coach in teams[team]["coaches"]])
	if(team in extra_teams):
		extra_team_names.append(team_name)

	team_rating=0.0
	for player in teams[team]["players"]:
		player_fn, player_ln = player.split()[0], " ".join(player.split()[1:]).lower()
		team_rating+=float(players[(player_ln,player_fn)]["rating"])
		ofh.write(",".join([team_name, \
					  		players[(player_ln, player_fn)]["PlayerID"],"","", \
							player,str(players[(player_ln, player_fn)]["rating"]),"",""])+"\n")
		
		rfh.write("\t".join([team_name,player,str(players[(player_ln, player_fn)]["rating"]),str((player_ln,player_fn) in extra_players)])+"\n")

	team_rating = team_rating/float(len(teams[team]["players"]))
	tfh.write(f"{team_name}\t{team_rating:.2f}\n")		
	for coach in teams[team]["coaches"]:
		if coach not in coach_data:
			print("Coach Missing in Personnel Data: "+coach)
			continue
		ofh.write(",".join([team_name,"" ,coach_data[coach]["VolunteerID"],coach_data[coach]["VolunteerTypeId"],"",coach_data[coach]["Team Personnel Name"],coach_data[coach]["Team Personnel Role"]])+"\n")

if(len(extra_team_names)>0):
	efh = open(DIVISION+"/"+DIVISION+"_Extra_Teams.txt",'w')
	for team in extra_team_names:
		efh.write(team+"\n")

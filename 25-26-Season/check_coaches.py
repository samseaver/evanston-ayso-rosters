#!/usr/bin/env python
import csv

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('division', help="Division")
args = parser.parse_args()
DIVISION = args.division

# get coach pairing requests and data
coach_pair_File = open(DIVISION+"/"+DIVISION+"_Coaches.tsv")
coach_pairs = csv.DictReader(coach_pair_File,delimiter='\t')
teams = {}
for line in coach_pairs:
	coach_first = line["First Name"].strip().lower() 
	coach_last = line["Last Name"].strip().lower()
	coach = coach_first + " " + coach_last
	team_index = line["Team"]
	if team_index == "TBD":
		continue
	
	if team_index not in teams:
		teams[team_index] = {"coaches":[coach], "players":[], "rating":[] , "gender":[], "age":[]}
	else:
		teams[team_index]["coaches"].append(coach)

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

for team in teams:
	for coach in teams[team]["coaches"]:
		if coach not in coach_data:
			print("Coach Missing in Personnel Data: "+coach)
			continue

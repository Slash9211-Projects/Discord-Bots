import discord, time, datetime, asyncio, random
from pymongo import MongoClient
from discord.utils import get

cluster = MongoClient('') #Removed connection string for security reasons

db = cluster['minecraft']

collection = db['report']
playerDatabase = db['player']
serverStats = db['stats']
gangDatabase = db['gang']

TOKEN = '' #Removed token for security reasons

client = discord.Client()

categoryName = 'Tickets'

channels = {}

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	if message.content.startswith('!ticketinfo'):
		# Make sure it's in the ticket-research channel
		if message.channel.id == 705678081007812628:
			# Check if their in the support role
			if discord.utils.get(message.guild.roles, name="Support") in message.author.roles:
				ticketID = int(message.content.replace('!ticketinfo ', ''))

				# Check if the ticket exists
				ticket = db.report.find_one({"ID": ticketID})

				if ticket != None:
					reporter = ticket.get("REPORTER")
					details = ticket.get("REPORT")
					date = str(ticket.get("DATE"))
					resolved = ticket.get("RESOLVED")
					resolution = ticket.get("RESOLUTION")

					ticketInfo = discord.Embed(
						title=f'Ticket #{ticketID}',
						colour=discord.Colour.blue()
					)

					ticketInfo.add_field(name='Details', value=f'{details}', inline=False)
					ticketInfo.add_field(name='Reporter', value=f'{reporter}', inline=True)
					ticketInfo.add_field(name='Date', value=f'{date}', inline=True)
					ticketInfo.add_field(name='Resolved', value=f'{resolved}', inline=True)

					if resolved:
						ticketInfo.add_field(name='Resolution', value=f'{resolution}', inline=False)

					await message.channel.send(embed=ticketInfo)
				else:
					await message.channel.send("That ticket doesn't exist!")

	elif message.content.startswith('!ticket'):
		#Verify that it's in the correct text-channel
		if message.channel.id == 705677981053616149:
			# Get next ticket number from the database and update database total
			ticketID = int(db.report.find_one({"REPORT_STATS": True}).get("TOTAL_REPORTS")) + 1
			collection.update_many({"REPORT_STATS": True}, {"$set": {"TOTAL_REPORTS": ticketID}})

			# Get the report details from the command
			details = message.content.replace("!ticket ", "")
			reporter = message.author.id
			today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

			# Upload all the ticket data to the database
			data = {"ID": ticketID, "REPORTER": reporter, "REPORT": details, "DATE": today, "CREATED": False, "RESOLVED": False, "RESOLUTION": ""}
			collection.insert_one(data)

			await createTicketChannel(ticketID, message.guild)
			await message.delete()

	elif message.content.startswith("!resolve"):
		# Check if the channel is a ticket channel
		if "ticket-" in message.channel.name:
			#Check if their in the support group
			if message.guild.get_role(706273768137556008) in message.author.roles:
				# Get the ticket ID from the channel name (Ex: Ticket-1)
				ticketID = int(message.channel.name.split("-")[1])

				# Verify the ticket exists
				if db.report.find_one({"ID": ticketID}) != None:
					resolution = message.content.replace("!resolve ", "")

					# Mark the report as resolved with its resolution
					collection.update_many({"ID": ticketID}, {"$set": {"RESOLVED": True}})
					collection.update_many({"ID": ticketID}, {"$set": {"RESOLUTION": resolution}})
					await message.channel.delete()

	elif message.content.startswith("!linked"):
		# Check if their discord has been linked yet
		playerData = db.player.find_one({'DISCORD_ID': str(message.author.id)})
		if playerData != None:
			#Get their staff rank
			staff = playerData.get("STAFF")
			if staff  != "NONE":
				staffRole = message.guild.get_role(int(db.rank.find_one({'RANK': staff}).get("DISCORD_ID")))
				if staffRole not in message.author.roles:
					await message.author.add_roles(staffRole)

			#Get their donator rank
			rank = playerData.get("RANK")
			if rank != "NONE":
				rankRole = message.guild.get_role(int(db.rank.find_one({'RANK': rank}).get("DISCORD_ID")))
				if rankRole not in message.author.roles:
					await message.author.add_roles(rankRole)

	elif message.content.startswith("!gang"):
		# Look for the gang in the database
		gangName = message.content.replace("!gang ", "")
		gangData = db.gang.find_one({"NAME": gangName})

		if (gangData != None):
			description = gangData.get("DESCRIPTION")
			balance = gangData.get("BALANCE")

			# Convert all members UUID to their name
			leader = "**" + db.player.find_one({"UUID": gangData.get("LEADER")}).get("IGN")

			members = leader

			for officer in gangData.get("OFFICERS"):
				members += " *" + db.player.find_one({"UUID": officer}).get("IGN")

			for member in gangData.get("MEMBERS"):
				members += " " + db.player.find_one({"UUID": member}).get("IGN")

			gangInfo = discord.Embed(
				title=f'Gang {gangName}',
				colour=discord.Colour.blue()
			)

			gangInfo.add_field(name='Description', value=f'{description}', inline=True)
			gangInfo.add_field(name='Balance', value=f'{balance}', inline=True)
			gangInfo.add_field(name='Members', value=f'{members}', inline=False)

			await message.channel.send(embed=gangInfo)
		else:
			await message.channel.send("That gang doesn't exist!")

	elif message.content.startswith('!link'):
		code = random.randrange(9999, 100000)

		username = message.content
		username = username.replace('!link ', '')
		DISCORD_ID = message.author.id

		playerData = db.player.find_one({'IGN': username})
		if playerData != None:
			if playerData.get('DISCORD_ID') == '':
				playerDatabase.update_many({'IGN': username}, {"$set": {'DISCORD_CODE': f'{code}:{DISCORD_ID}'}})

				# Send the player a message of the code and instructions
				await message.author.send(code)
		await message.delete()

	elif message.content.startswith('!clear'):
		# Check if their an admin/developer/owner
		if discord.utils.get(message.guild.roles, name="ADMIN") or discord.utils.get(message.guild.roles, name="DEVELOPER") or discord.utils.get(message.guild.roles, name="OWNER") in message.author.roles:
			await message.channel.purge(limit=100)

	elif message.content.startswith('!player'):
		playerName = message.content.replace('!player', '')
		playerData = db.player.find_one({"IGN": playerName})

		if (playerData != None):

			playerInfo = discord.Embed(
				title=f'Player {playerName}',
				colour=discord.Colour.blue()
			)

			playerInfo.add_field(name="TEST", value="TEST", inline=False)

			await message.channel.send(embed=playerInfo)

	elif message.content.startswith('!privatechannel'):
		if (message.author.voice): #Check if their connected
			id = random.randrange(9999, 100000)
			password = message.content.split(' ')[1]

			#Need to make sure that the ID isn't already taken, if so redo the number.

			await message.delete()

			await createChannel(id, password, message.guild, message.author)
		else:
			await message.channel.send(message.author.mention + " You must be connected to a voice-channel to create a private channel!")

	elif message.content.startswith('!join'):
		if (message.author.voice):
			info = message.content.split(' ')
			id = info[1]
			password = info[2]

			if (channels.get(int(id)).split(':')[1] == password):
				channel = message.guild.get_channel(int(channels.get(int(id)).split(':')[0]))
				await channel.set_permissions(message.author, view_channel=True, connect=True)
				await message.author.move_to(channel)

			await message.delete()

#############################################################################

async def createChannel(id, password, guild, member):
	if member.voice:
		# Create the channel under the category
		category = discord.utils.get(guild.categories, name="Private")
		channel = await guild.create_voice_channel(f'Private-{id}', category=category)

		# Save the information
		channels[int(f'{id}')] = str(channel.id) + f':{password}'

		await channel.set_permissions(member, view_channel=True, connect=True)
		await member.move_to(channel)

@client.event
async def on_voice_state_update(member, before, after):
	if before.channel != None:
		if 'Private' in before.channel.name:
			if channels.get(int(before.channel.name.replace('Private-', ''))) :
				id = int(before.channel.name.replace('Private-', ''))

				if len(before.channel.members) == 0: #Check if there's no one in the channel before deleting
					await before.channel.delete()
					channels.pop(id)

###############################################################################

async def setServerStats(guild):
	await client.wait_until_ready()

	while not client.is_closed():
		#Set the players online stat
		await guild.get_channel(706691331665166348).edit(name="Players Online: " + str(serverStats.find_one({'STATS': True}).get('PLAYERS_ONLINE')))

		#Set the staff online stat
		await guild.get_channel(706695201053474848).edit(name="Staff Online: " + str(serverStats.find_one({'STATS': True}).get('STAFF_ONLINE')))

		await asyncio.sleep(60)

async def checkForTickets(guild):
	await client.wait_until_ready()

	while not client.is_closed():
		#Verify there's tickets in there before looping through them
		if db.report.find({"CREATED": False}).count() != 0:

			# Loop through each ticket that hasn't been created yet and create it's text channel
			for x in range(0, db.report.find({"CREATED": False}).count()):
				await createTicketChannel(db.report.find_one({"CREATED": False}).get("ID"), guild)

		await asyncio.sleep(60)

async def createTicketChannel(id, guild):
	report = db.report.find_one({"ID": id})

	if report != None:
		if report.get("CREATED") != True:
			reporter = report.get("REPORTER")
			details = report.get("REPORT")

			collection.update_many({"ID": id}, {"$set": {"CREATED": True}})

			category = discord.utils.get(guild.categories, name="Tickets")
			channel = await guild.create_text_channel(f'Ticket-{id}', category=category)

			await channel.set_permissions(discord.utils.get(guild.roles, name="Support"), read_messages=True, send_messages=True, view_channel=True, attach_files=True, embed_links=True)

			ticketInfo = discord.Embed(
				title= f'Ticket #{id}',
				colour = discord.Colour.blue()
			)

			ticketInfo.add_field(name='Details', value=f'{details}', inline=False)
			ticketInfo.add_field(name='Reporter', value=f'{reporter}', inline= True)
			ticketInfo.add_field(name='Support', value=discord.utils.get(guild.roles, name="Support").mention)

			member = guild.get_member(int(reporter))
			if member != None:
				await channel.set_permissions(member,read_messages=True, send_messages=True, view_channel=True, attach_files=True, embed_links=True)

			await channel.send(embed=ticketInfo)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

	privateChannels = 0
	await client.change_presence(activity=discord.Game(name='Customer Service'))

	client.loop.create_task(checkForTickets(client.get_guild(705674859400659015)))
	client.loop.create_task(setServerStats(client.get_guild(705674859400659015)))


client.run(TOKEN)
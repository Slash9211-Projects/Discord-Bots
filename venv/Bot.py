import discord, time, datetime, asyncio, random, locale
from discord.ext import commands
from pymongo import MongoClient
from discord.utils import get

TOKEN = ''
client = commands.Bot(command_prefix='!')

# MongoDB Stuff
mongo = MongoClient(
    '')
mongoDB = mongo['minecraft']

# Private Channels
channels = {}

# Economy Format
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Channel IDs
bot_commands_channel = 705675337035546656
tickets_channel = 705677981053616149
ticket_research_channel = 705678081007812628
general_channel = 705675312326770709

####################
# Ticket Mechanics #
####################

@client.command(name='ticket')
async def create_ticket(ctx):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != tickets_channel):
        return

    # Get the next ticket number from the database and then update the total tickets
    ID = int(mongoDB.report.find_one({'REPORT_STATS': True}).get('TOTAL_REPORTS')) + 1
    mongoDB.report.update_many({'REPORT_STATS': True}, {'$set': {'TOTAL_REPORTS': ID}})

    # Get the report details/reporter/date
    details = ctx.message.content.replace('!ticket ', '')
    reporter = ctx.author.id
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Upload the ticket to the database
    data = {"ID": ID, "REPORTER": reporter, "REPORT": details, "DATE": today, "CREATED": False, "RESOLVED": False,
            "RESOLUTION": ""}
    mongoDB.report.insert_one(data)

    # Create the ticket channel
    await create_ticket_channel(ID, ctx.guild)

    # Delete the message
    await ctx.message.delete()

@client.command(name='resolve')
@commands.has_role('Support')
async def resolve_ticket(ctx):
    # Check if the channel is a ticket_channel
    if 'ticket-' in ctx.channel.name:
        # Get the ticket id from the channel name
        id = int(ctx.channel.name.split('-')[1])

        # Verify the ticket exists in the database
        if mongoDB.report.find_one({'ID': id}) != None:
            # Get the resolution from the command
            resolution = ctx.message.content.replace('!resolve ', '')

            # Make sure that the resolution isn't empty
            if resolution != '':
                # Update the ticket in the database to be resolved w/ its resolution
                mongoDB.report.update_many({'ID': id}, {'$set': {'RESOLVED': True}})
                mongoDB.report.update_many({'ID': id}, {'$set': {'RESOLUTION': resolution}})

                # Delete the ticket_channel
                await ctx.channel.delete()

            else:
                await ctx.channel.send("You must include a resolution for the ticket!")


# Get ticket info from the database and send it back as an embedded message
@client.command(name='ticketinfo')
@commands.has_role('Support')
async def getTicketInfo(ctx, id='0', channel_name='ticket-research'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != ticket_research_channel):
        return

    ID = int(id)

    ticket = mongoDB.report.find_one({'ID': ID})

    # Check if the ticket actually exists in the database
    if ticket != None:
        reporter = ticket.get("REPORTER")
        details = ticket.get("REPORT")
        date = str(ticket.get("DATE"))
        resolved = ticket.get("RESOLVED")
        resolution = ticket.get("RESOLUTION")

        # Create the embedded message and send it
        info = discord.Embed(
            title=f'Ticket #{ID}',
            colour=discord.Colour.blue()
        )

        info.add_field(name='Details', value=details, inline=False)
        info.add_field(name='Reporter', value=reporter, inline=True)
        info.add_field(name='Date', value=date, inline=True)
        info.add_field(name='Resolved', value=resolved, inline=True)

        if resolved:
            info.add_field(name='Resolution', value=resolution, inline=False)

        # Send the ticket details into the text_channel
        await ctx.channel.send(embed=info)
    else:
        await ctx.channel.send("That ticket doesn't exist!")


# Creates the specified tickets text_channel if it hasn't been made yet
async def create_ticket_channel(id, guild):
    # Get the ticket from the database
    ticket = mongoDB.report.find_one({'ID': id})

    # Make sure the ticket exists and hasn't been created yet
    if ticket != None:
        if ticket.get('CREATED') != True:
            reporter = ticket.get('REPORTER')
            details = ticket.get('REPORT')

            # Set the ticket to created in the database
            mongoDB.report.update_many({'ID': id}, {'$set': {'CREATED': True}})

            # Create the ticket text_channel
            channel = await guild.create_text_channel(f'Ticket-{id}',
                                                      category=discord.utils.get(guild.categories, name='Tickets'))

            # Add the support group to the channel
            await channel.set_permissions(discord.utils.get(guild.roles, name="Support"), read_messages=True,
                                          send_messages=True, view_channel=True, attach_files=True, embed_links=True)

            # Create the embedded ticket details message
            info = discord.Embed(
                title=f'Ticket #{id}',
                colour=discord.Colour.blue()
            )

            info.add_field(name='Details', value=details, inline=False)
            info.add_field(name='Reporter', value=reporter, inline=True)
            info.add_field(name='Support', value=discord.utils.get(guild.roles, name="Support").mention)

            # Check if the 'reporter' is a member of the discord, if so add them to the channel
            member = guild.get_member(int(reporter))
            if member != None:
                await channel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True,
                                              attach_files=True, embed_links=True)

            await channel.send(embed=info)


# Continously checks for tickets that haven't been made yet
async def check_for_tickets(guild):
    await discord.Client().wait_until_ready()

    while not discord.Client().is_closed():
        tickets = mongoDB.report.find({'CREATED': False}).count()

        # Verify there's tickets that are needing to be created
        if tickets != 0:
            # Loop through each ticket that hasn't been created yet and create its text channel
            for x in range(0, tickets):
                await create_ticket_channel(mongoDB.report.find_one({'CREATED': False}).get('ID'), guild)

        # Repeat every 60 seconds
        await asyncio.sleep(60)


#############################
# Private Channel Mechanics #
#############################

@client.command(name='privatechannel')
async def request_private_channel(ctx, password='password'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Delete the message
    await ctx.message.delete()

    # Make sure that the requestor is connected to a voice channel
    if ctx.author.voice:
        # Generate a channel ID
        id = random.randrange(9999, 100000)

        # Create the voice channel
        await create_private_channel(id, password, ctx.guild, ctx.author)
    else:
        await ctx.channel.send(
            ctx.author.mention + " You must be connected to a voice-channel to create a private-channel!")


@client.command(name='join')
async def join_private_channel(ctx, id='0', password='password'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Delete the message
    await ctx.message.delete()

    # Make sure that the user is connected to a voice channel
    if ctx.author.voice:
        id = int(id)

        # Verify the channel exists and if the password is correct
        if channels.get(id).split(':')[1] == password:
            # Get the voice_channel and text_channel
            channel = ctx.guild.get_channel(int(channels.get(id).split(':')[0].split(',')[0]))
            textChannel = ctx.guild.get_channel(int(channels.get(id).split(':')[0].split(',')[1]))

            # Give the user permission to the channel and move them to it
            await channel.set_permissions(ctx.author, view_channel=True, connect=True)
            await textChannel.set_permissions(ctx.author, read_messages=True, send_messages=True, view_channel=True,
                                              attach_files=True, embed_links=True)
            await ctx.author.move_to(channel)


async def create_private_channel(id, password, guild, member):
    # Verify that the requester is still connected
    if member.voice:
        # Create the channel uder the 'Private' category
        channel = await guild.create_voice_channel(f'Private-{id}',
                                                   category=discord.utils.get(guild.categories, name='Private'))
        textChannel = await guild.create_text_channel(f'Private-{id}',
                                                      category=discord.utils.get(guild.categories, name='Private'))

        # Save the password and channel id in the 'channels' dictionary w/ the assigned id
        channels[int(id)] = str(channel.id) + ',' + str(textChannel.id) + f':{password}'

    # Give the requester permission to the channel and move them into it
    await channel.set_permissions(member, view_channel=True, connect=True)
    await textChannel.set_permissions(member, read_messages=True, send_messages=True, view_channel=True,
                                      attach_files=True, embed_links=True)
    await member.move_to(channel)


# User disconnects from a voice channel
@client.event
async def on_voice_state_update(member, before, after):
    # Make sure that the channel they left exists
    if before.channel != None:
        # Check if it was a priavate channel
        if 'Private-' in before.channel.name:
            # Get the channel id from the channel name and verify that it's in the private channels dictionary
            id = int(before.channel.name.replace('Private-', ''))
            if channels.get(id):
                # Check if there's anyone connected to the channel still, if not delete it and remove it from the channels dictionary
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    await before.channel.guild.get_channel(int(channels.get(id).split(':')[0].split(',')[1])).delete()
                    channels.pop(id)


##############################
# Minecraft Server Mechanics #
##############################

@client.command(name='link')
async def link_minecraft(ctx, minecraft_ign='default'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Generate a 5-digit code for them to use in-game
    code = random.randrange(9999, 100000)

    discord_id = ctx.author.id

    # Verify that the specified IGN exists in the database
    playerData = mongoDB.player.find_one({'IGN': minecraft_ign})
    if playerData != None:
        # Verify that their discord isn't already linked
        if playerData.get('DISCORD_ID') == '':
            mongoDB.player.update_many({'IGN': minecraft_ign}, {'$set': {'DISCORD_CODE': f'{code}:{discord_id}'}})

            # Send the code to the user with further instructions
            await ctx.author.send(
                f'Type the following command when connected to the Minecraft server to finish linking your accounts \n```/discord {code}```')
        else:
            await ctx.channel.send(
                ctx.author.mention + ' Your accounts are already linked together! To unlink your account please create a ticket (!ticket <details>)')

    # Delete the message
    await ctx.message.delete()


@client.command(name='linked')
async def linked_minecraft(ctx, minecraft_ign='default'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Check if their discord id is linked to an account
    playerData = mongoDB.player.find_one({'DISCORD_ID': str(ctx.author.id)})
    if playerData != None:

        # Get their staff rank and assign it as a role if they don't have it
        staff = playerData.get('STAFF')
        if staff != 'NONE':
            staffRole = message.guild.get_role(int(mongoDB.rank.find_one({'RANK': staff}).get('DISCORD_ID')))
            if staffRole not in ctx.author.roles:
                await ctx.author.add_roles(staffRole)

        # Get their donator rank and assign it as a role if they don't have it
        rank = playerData.get('RANK')
        if rank != 'NONE':
            rankRole = message.guild.get_role(int(mongoDB.rank.find_one({'RANK': rank}).get('DISCORD_ID')))
            if rankRole not in ctx.author.roles:
                await ctx.author.add_roles(rankRole)

        await ctx.author.send('Your Discord roles have been updated!')


@client.command(name='gang')
async def get_gang_info(ctx, gang_name='gang'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Verify that the gang exists in the database
    gangData = mongoDB.gang.find_one({'NAME': gang_name})
    if gangData != None:
        # Get the gangs information, put it into an embedded message, and send the message
        description = gangData.get('DESCRIPTION')
        balance = gangData.get('BALANCE')

        # Convert all members UUID to their name
        leader = '**' + mongoDB.player.find_one({'UUID': gangData.get('LEADER')}).get('IGN')

        members = leader

        for officer in gangData.get('OFFICERS'):
            members += ' *' + mongoDB.player.find_one({'UUID': officer}).get('IGN')

        for member in gangData.get('MEMBERS'):
            members += ' ' + mongoDB.player.find_one({'UUID': member}).get('IGN')

        info = discord.Embed(
            title=f'Gang {gang_name}',
            colour=discord.Colour.blue()
        )

        info.add_field(name='Description', value=description, inline=False)
        info.add_field(name='Members', value=members, inline=False)
        info.add_field(name='Balance', value=balance, inline=False)

        await ctx.channel.send(embed=info)
    else:
        await ctx.channel.send(ctx.author.mention + " That gang doesn't exist!")


@client.command(name='player')
async def get_player_info(ctx, player_name='player'):
    # Verify that the command was sent in the correct channel
    if (ctx.channel.id != bot_commands_channel):
        return

    # Verify that the player exists in the database
    playerData = mongoDB.player.find_one({'IGN': player_name})
    if playerData != None:
        # Create the embedded message of the player info and send it
        info = discord.Embed(
            title=f"{player_name}'s Game Stats",
            colour=discord.Colour.blue()
        )

        info.add_field(name='Level', value=playerData.get('LEVEL'), inline=True)
        info.add_field(name='XP', value=playerData.get('EXPERIENCE'), inline=True)

        # Check if their in a valid gang, if so grab its name
        gangData = mongoDB.gang.find_one({'ID': playerData.get('GANG_ID')})
        if gangData != None:
            info.add_field(name='Gang', value=gangData.get('NAME'), inline=False)

        if playerData.get('RANK') != 'NONE':
            info.add_field(name='Rank', value=playerData.get('RANK'), inline=False)

        if playerData.get('STAFF') != 'NONE':
            info.add_field(name='Staff', value=playerData.get('STAFF'), inline=True)

        info.add_field(name='Balance', value=f'${playerData.get("BALANCE"):n}', inline=False)

        info.add_field(name='Play Time', value=convert_seconds_to_DHMS(playerData.get('PLAY_TIME')), inline=False)

        if int(playerData.get('PRESTIGE')) > 0:
            info.add_field(name='Prestige', value=playerData.get('PRESTIGE'), inline=False)

        await ctx.channel.send(embed=info)
    else:
        await ctx.channel.send(ctx.author.mention + " That player doesn't exist or hasn't played on the server before!")


####################
# Other Mechanics #
####################

@client.command(name='clear')
@commands.has_any_role('MODERATOR', 'ADMIN', 'DEVELOPER', 'OWNER')
async def clear(ctx, amount=100):
    # Clear x amount of messages out of the channel the command was used in
    await ctx.channel.purge(limit=int(amount))

# Convert seconds to DAYS HOURS MINUTE SECONDS
def convert_seconds_to_DHMS(seconds_total):
    days = seconds_total / 86400
    hours = (seconds_total % 86400) / 3600
    minutes = ((seconds_total % 86400) % 3600) / 60
    seconds = ((seconds_total % 86400) % 3600) % 60

    return '%dd %02dh %02dm %02ds' % (days, hours, minutes, seconds)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    guild = client.get_guild(705674859400659015)

    await client.change_presence(activity=discord.Game(name='play.google.com'))

    client.loop.create_task(check_for_tickets(guild))


client.run(TOKEN)

import discord
import json
from discord.ext import commands
from bot import is_admin

# Create a dictionary to store apartment data
apartments = {}

def save_apartments():
    # Save the apartments data to a file
    with open('apartments.json', 'w') as file:
        json.dump(apartments, file)

def load_apartments():
    # Load the apartments data from a file
    try:
        with open('apartments.json', 'r') as file:
            apartments.update(json.load(file))
    except FileNotFoundError:
        pass

def setup(bot):
    @bot.slash_command(name='createhouse', description='Create a new apartment')
    @commands.check(is_admin)
    async def createhouse(ctx, name: str, max_residents: int):
        if name in apartments:
            await ctx.respond(f"An apartment with the name '{name}' already exists.")
        else:
            apartments[name] = {
                'max_residents': max_residents,
                'current_residents': 0,
                'waiting_list': 0
            }
            save_apartments()
            await ctx.respond(f"Apartment '{name}' created successfully.")

    @bot.slash_command(name='addresidents', description='Add new residents to an apartment')
    @commands.check(is_admin)
    async def addresidents(ctx, name: str, num_residents: int):
        if name not in apartments:
            await ctx.respond(f"Apartment '{name}' does not exist.")
        else:
            apartment = apartments[name]
            available_slots = apartment['max_residents'] - apartment['current_residents']
            if num_residents <= available_slots:
                apartment['current_residents'] += num_residents
                save_apartments()
                await ctx.respond(f"{num_residents} resident(s) added to apartment '{name}'.")
            else:
                apartment['current_residents'] = apartment['max_residents']
                apartment['waiting_list'] += num_residents - available_slots
                save_apartments()
                await ctx.respond(f"{available_slots} resident(s) added to apartment '{name}'. {num_residents - available_slots} resident(s) added to the waiting list.")

    @bot.slash_command(name='vipapartment', description='Show a list of apartments')
    @commands.check(is_admin)
    async def vipapartment(ctx):
        if not apartments:
            await ctx.respond("No apartments found.")
        else:
            embed = discord.Embed(title='VIP Apartments', color=discord.Color.blue())
            for name, apartment in apartments.items():
                embed.add_field(
                    name=name,
                    value=f"Max Residents: {apartment['max_residents']}\nCurrent Residents: {apartment['current_residents']}\nWaiting List: {apartment['waiting_list']}",
                    inline=False
                )
            await ctx.respond(embed=embed)

# Load the apartments data when the bot starts
load_apartments()

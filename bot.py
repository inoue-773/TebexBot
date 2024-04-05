import discord
import os
import requests
import json
from discord.ext import commands
from dotenv import load_dotenv
import socket
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TEBEX_SECRET = os.getenv('TEBEX_SECRET')
ADMIN_ROLE_IDS = [int(role_id) for role_id in os.getenv('ADMIN_ROLE_IDS').split(',')]
SERVER_IP = os.getenv('LIVE_SERVER_IP')


intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

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

def is_admin(ctx):
    return any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

@bot.slash_command(name='kakunin', description='Transaction IDから情報を取得')
@commands.check(is_admin)
async def kakunin(ctx, transaction_id: discord.Option(str, "tbxから始まるTransaction IDを入力")):
    url = f'https://plugin.tebex.io/payments/{transaction_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()

        # Convert the date to JST
        date_str = data['date']
        date_utc = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        date_jst = date_utc + timedelta(hours=9)
        date_jst_str = date_jst.strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(
            title=f"🔍 Information for {transaction_id}",
            description="Here are the details of the transaction:",
            color=discord.Color.blue()
        )

        embed.add_field(name="💰 Price", value=data['amount'], inline=True)

        status = data['status']
        if status.lower() == 'complete':
            status_text = f"```🟢 {status}```"
        else:
            status_text = f"```🔴 {status}```"
        embed.add_field(name="📊 Status", value=status_text, inline=True)

        embed.add_field(name="📅 Date (JST)", value=date_jst_str, inline=False)

        player_name = data['player']['name']
        embed.add_field(name="👤 Tebex Username", value=player_name, inline=False)

        package_names = ', '.join([package['name'] for package in data['packages']])
        embed.add_field(name="🎁 Package Name(s)", value=package_names, inline=False)

        embed.set_footer(
            text="Powered By NickyBoy",
            icon_url="https://i.imgur.com/QfmDKS6.png"
        )

        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve payment information.')

@bot.slash_command(name='products', description='寄付できる返礼品の一覧')
@commands.check(is_admin)
async def products(ctx):
    url = 'https://plugin.tebex.io/packages'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        packages = response.json()
        embeds = []
        current_embed = None

        for index, package in enumerate(packages, start=1):
            if index % 25 == 1:
                if current_embed:
                    embeds.append(current_embed)
                current_embed = discord.Embed(title='返礼品一覧', color=0XE16941, description='返礼品の一覧')

            package_name = package['name']
            package_price = package['price']
            package_category = package['category']['name']
            package_id = package['id']
            package_info = f"Price: {package_price}, ID: {package_id}, Category: {package_category}"
            current_embed.add_field(name=package_name, value=package_info, inline=False)

        if current_embed:
            embeds.append(current_embed)

        if embeds:
            for embed in embeds:
                await ctx.respond(embed=embed)
        else:
            await ctx.respond('No products found.')
    else:
        await ctx.respond('Failed to retrieve product information.')

@bot.slash_command(name='search', description='Tebex IDから情報を取得')
@commands.check(is_admin)
async def search(ctx, tebex_id: discord.Option(str, "Tebex IDをここに入力 Transaction IDではない")):
    url = f'https://plugin.tebex.io/user/{tebex_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()
        embed = discord.Embed(title=f'Player Information for {tebex_id}')
        embed.add_field(name='Username', value=data['player']['username'])
        embed.add_field(name='Ban Count', value=data['banCount'])
        embed.add_field(name='Chargeback Rate', value=data['chargebackRate'])
        total_purchases = '\n'.join([f"{currency}: {amount}" for currency, amount in data['purchaseTotals'].items()])
        embed.add_field(name='Total Purchases', value=total_purchases)
        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve player information.')

@bot.slash_command(name='updateproduct', description='返礼品の情報を更新')
@commands.check(is_admin)
async def updateproduct(ctx, package_id: discord.Option(int, "返礼品IDを入力 分からない場合は/productsで確認"), enabled: discord.Option(bool, "disabledの場合寄付の受け付けを中止"), name: discord.Option(str, "新しい返礼品の名前"), price: discord.Option(float, "新しい返礼品の価格")):
    url = f'https://plugin.tebex.io/package/{package_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'disabled': not enabled,
        'name': name,
        'price': price
    }
    response = requests.put(url, headers=key, json=data)

    if response.status_code == 204:
        status = 'enabled' if enabled else 'disabled'
        await ctx.respond(f'Package {package_id} has been updated. Status: {status}, Name: {name}, Price: {price}')
    else:
        await ctx.respond('Failed to update the package.')

@bot.slash_command(name='createurl', description='決済URLを作成')
@commands.check(is_admin)
async def createurl(ctx, package_id: discord.Option(str, "返礼品IDを入力 分からない場合は/productsで確認"), tebex_id: discord.Option(str, "Tebex IDを入力")):
    url = 'https://plugin.tebex.io/checkout'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'package_id': package_id,
        'username': tebex_id
    }
    response = requests.post(url, headers=key, json=data)

    if response.status_code == 201:
        checkout_data = response.json()
        checkout_url = checkout_data['url']
        expires_at = checkout_data['expires']
        embed = discord.Embed(title='Checkout URL Created', color=discord.Color.green())
        embed.add_field(name='URL', value=checkout_url)
        embed.add_field(name='Expires At', value=expires_at)
        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to create the checkout URL.')

@bot.slash_command(name='recentpayments', description='直近25件の決済の一覧表示')
@commands.check(is_admin)
async def recentpayments(ctx):
    url = 'https://plugin.tebex.io/payments?paged=1'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()
        payments = data['data'][:25]  # Truncate the list to the first 25 payments

        embed = discord.Embed(title='Recent Payments', color=discord.Color.blue())

        payment_info = ""
        for index, payment in enumerate(payments, start=1):
            transaction_id = payment.get('id', 'N/A')  # Use 'N/A' as default if 'id' is not found
            timestamp = payment.get('date', 0)  # Use 0 as default if 'date' is not found
            amount = payment.get('amount', 'N/A')  # Use 'N/A' as default if 'amount' is not found
            currency = payment.get('currency', {}).get('iso_4217', 'N/A')  # Use 'N/A' as default if 'currency' or 'iso_4217' is not found
            status = payment.get('status', 'N/A')  # Use 'N/A' as default if 'status' is not found
            player_name = payment.get('player', {}).get('name', 'N/A')  # Use 'N/A' as default if 'player' or 'name' is not found

            # Convert the timestamp to a datetime object
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")

            # Add 9 hours to convert from UTC to JST
            jst_dt = dt + timedelta(hours=9)

            # Format the datetime as a string in JST
            jst_time = jst_dt.strftime("%Y-%m-%d %H:%M:%S")

            package_names = ', '.join([package.get('name', 'N/A') for package in payment.get('packages', [])])  # Use 'N/A' as default if 'packages' or 'name' is not found

            payment_info += f"**Transaction ID: {transaction_id}**\nPlayer: {player_name}\nAmount: {amount} {currency}\nPackage(s): {package_names}\nStatus: {status}\nDate (JST): {jst_time}\n\n"

            if index % 5 == 0 or index == len(payments):
                embed.add_field(name=f"Payments {index-4} to {index}", value=payment_info, inline=False)
                payment_info = ""

        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve recent payments.')



# apartment management

@bot.slash_command(name='createhouse', description='新規VIPハウスを作成')
@commands.check(is_admin)
async def createhouse(ctx, name: discord.Option(str, "VIPハウスの名前"), max_residents: discord.Option(int, "入居できる人数の最大値")):
    if name in apartments:
        await ctx.respond(f"すでに '{name}' は存在します。同じカテゴリで複数のVIPハウスを作る場合、高級VIPハウス(1000番)、高級VIPハウス(2000番)などと番地を入れて名前の被りを回避してください。", ephemeral=True)
    else:
        apartments[name] = {
            'max_residents': max_residents,
            'current_residents': 0,
            'waiting_list': 0
        }
        save_apartments()
        await ctx.respond(f"Apartment '{name}' created successfully.", ephemeral=True)

@bot.slash_command(name='addresidents', description='Add new residents to an apartment')
@commands.check(is_admin)
async def addresidents(ctx, name: str, num_residents: int):
    if name not in apartments:
        await ctx.respond(f"Apartment '{name}' は存在しません", ephemeral=True)
    else:
        apartment = apartments[name]
        available_slots = apartment['max_residents'] - apartment['current_residents']
        if num_residents <= available_slots:
            apartment['current_residents'] += num_residents
            save_apartments()
            await ctx.respond(f"{num_residents} resident(s) added to apartment '{name}'.", ephemeral=True)
        else:
            apartment['current_residents'] = apartment['max_residents']
            apartment['waiting_list'] += num_residents - available_slots
            save_apartments()
            await ctx.respond(f"{available_slots} resident(s) added to apartment '{name}'. {num_residents - available_slots} resident(s) added to the waiting list.", ephemeral=True)

@bot.slash_command(name='vipapartment', description='VIPハウスの入居状況を表示')
async def vipapartment(ctx):
    if not apartments:
        await ctx.respond("VIPハウスが登録されていません")
    else:
        embed = discord.Embed(title='VIP Apartments', description='現在のVIPハウスの状況 超高級VIPはチケットにて随時受付中', color=discord.Color.yellow())
        for name, apartment in apartments.items():
            embed.add_field(
                name=f"🏠 {name}",
                value=f"最大入居可能人数: {apartment['max_residents']}\n現在の入居数: {apartment['current_residents']}\nキャンセル待ち: {apartment['waiting_list']}",
                inline=False
            )
            embed.set_thumbnail(url="https://i.imgur.com/sK2BAAO.png")
            embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name='updateresidents', description='VIPハウスの人数を更新')
@commands.check(is_admin)
async def updateresidents(ctx, name: discord.Option(str, "VIPハウスの名前"), updated_residents: discord.Option(int, "現在の入居数+キャンセル待ちの数")):
    if name not in apartments:
        await ctx.respond(f"Apartment '{name}' does not exist.")
    else:
        apartment = apartments[name]
        current_residents = apartment['current_residents']
        waiting_list = apartment['waiting_list']

        if updated_residents < current_residents:
            difference = current_residents - updated_residents
            if difference <= waiting_list:
                apartment['waiting_list'] -= difference
            else:
                apartment['waiting_list'] = 0
                apartment['current_residents'] = updated_residents
        else:
            apartment['current_residents'] = min(updated_residents, apartment['max_residents'])

        save_apartments()
        await ctx.respond(f" '{name}' の入居数がが更新されました", ephemeral=True)

@bot.slash_command(name='deletehouse', description='VIPハウスを削除')
@commands.check(is_admin)
async def deletehouse(ctx, name: str):
    if name not in apartments:
        await ctx.respond(f"Apartment '{name}' does not exist.", ephemeral=True)
    else:
        del apartments[name]
        save_apartments()
        await ctx.respond(f"Apartment '{name}' has been deleted.", ephemeral=True)


# ping system
@bot.slash_command(name='flecity', description='Check the status of the server')
async def flecity(ctx):
    await ctx.defer()  

    ip_address = SERVER_IP
    port = 30110

    try:
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Set a timeout of 5 seconds

        # Connect to the server
        result = sock.connect_ex((ip_address, port))

        if result == 0:
            status = '🟢 Online'
            color = discord.Color.green()
        else:
            status = '🔴 Offline'
            color = discord.Color.red()

    except socket.error:
        status = '🔴 Offline'
        color = discord.Color.red()

    finally:
        # Close the socket
        sock.close()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(title='Server Status', color=color)
    embed.add_field(name='Status', value=status, inline=False)
    embed.add_field(name='Time', value=current_time, inline=False)

    try:
        await ctx.followup.send(embed=embed)  
    except Exception as e:
        print(f"Error sending response: {str(e)}")
        await ctx.followup.send("An error occurred while sending the response. Please try again later.")


# Load the apartments data when the bot starts
load_apartments()

bot.run(TOKEN)

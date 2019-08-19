# bitmex-pairs_bot

Simple bot template for you to modify. This bot was designed for pairs trading between the Bitmex perpetual swap contracts and the futures. Pairs trading profits off market inefficiencies that occur around ratio between two cointigrated assets.

Please note this bot is offered AS IS and I take NO RESPONSIBILITY for any money you may lose or ANY OTHER BAD THINGS that might happen as a result of using or attempting to use this script.

With that said, if you want to ask me any questions about it I'll be happy to answer; just message at jb400 [at] tutanota.com. 

IMPORTANT:

Please do NOT use bot without modifying. It will certainly lose you money. The bot has some default values which are very unlikely to be profitable. You must design your own strategy, backtest it thoroughly and only then use it on the live market. Even then you should be aware that unexpected things can happen!

Browsing the code should be fairly obvious what to change. In particular:

Line58: test:True - this means the bot will run on the Testnet. Change to False to run on the real market. As I've said above, don't do this with the default values as you will certainly lose your money. 

Line59.60 - your API key goes here. The bot will not work without being logged in, for obvious reasons. When you make your API key in Bitmex dashboard, be sure not to enable withdrawals. The bot doesn't need or use them and you only create potential vulnerabilities. 

Line 23 - 27: Pairs and static ratio mean. If you want you could have the bot update and calculate the static ratio mean dynamically or manaully adjust it each day depending on your strategy. This is just a default placeholder value.

This bot connects to the Bitmex REST API which is rate-limited at 300 requests per 5 minutes. Simply run it using crontab at whatever time interval suits your strategy and it will ping the Bitmex server accordingly.

This is one of my earliest bots and should be quite simple to figure out. If you are interested in more complex bots, don't be shy about sending me a message. 






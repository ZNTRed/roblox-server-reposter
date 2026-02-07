import requests, time, random, json
from rich import print

message = open('message.txt').read()
config = json.load(
    open('config.json')
)

class VIP:
    def __init__(self):

        self.cookie = config['roblox']['cookie']
        self.user_id = config['roblox']['user_id']
        self.game_id = config['roblox']['game_id']
        self.required_badge_ids = config['roblox']['required_badge_ids']

        self.channel_id = config['discord']['channel_id']
        self.authorization = config['discord']['authorization']
        self.webhook_for_users_without_badges = config['discord']['webhook_for_users_without_badges']
        self.message_cooldown = config['discord']['message_cooldown']

        self.session = requests.Session()
        self.session.cookies['.ROBLOSECURITY'] = self.cookie

    def get_server_info(self):
        response = self.session.get(
            f'https://games.roblox.com/v1/games/{self.game_id}/private-servers?cursor=&sortOrder=Desc&excludeFullGames=false',
        )
        owned_servers = [server for server in response.json()['data'] if server['owner']['id'] == int(self.user_id)]

        if not owned_servers:
            raise RuntimeError("You do not own any VIP servers.")

        for server in owned_servers:
            if any(player['id'] == int(self.user_id) for player in server['players']):
                return server
        return owned_servers[0]


    def owned_check(self, user_id, badge_id):
        response = self.session.get(
            f'https://inventory.roblox.com/v1/users/{user_id}/items/Badge/{badge_id}'
        )
        return response.json()['data']


    def check_user_meets_requirements(self, users):
        for user in users:
            if not all(self.owned_check(user, badge_id) for badge_id in self.required_badge_ids):
                print(f"{user} potentially doesn't meet the requirement!")


    def send_to_discord(self, message):
        payload = {
            "mobile_network_type": "unknown",
            "content": message,
            "nonce": str(random.randint(345325252, 932894814993532)),
            "tts": False,
            "flags": 0
        }

        response = requests.post(
            f'https://canary.discord.com/api/v9/channels/{self.channel_id}/messages',
            headers = {
                'authorization': self.authorization
            }, json = payload
        )
        self.last_message_id = response.json()['id']


    def message_editor(self, message):
        response = requests.patch(
            f'https://canary.discord.com/api/v9/channels/{self.channel_id}/messages/{self.last_message_id}',
            json = {
                'content': message
            }, headers = {
                'authorization': self.authorization
            }
        )


    def main_loop(self):
        self.loop_count = 10

        while 1:
            server = self.get_server_info()

            player_count, max_player_count = server['playing'], server['maxPlayers']
            visible_players = len(server['players'])

            if player_count != visible_players:
                print(f'{player_count} players are in your server but only {visible_players} can be checked')

            if self.loop_count & 10:
                self.check_user_meets_requirements(
                    [player['id'] for player in server['players']]
                )

            new_message = message.replace('REPLACE', f'{player_count}/{max_player_count} players (**player count will auto-update every 30 sec and should be fairly accurate**)')

            if self.loop_count != 10:
                if self.last_player_array != [player_count, max_player_count]:
                    if hasattr(self, "last_message_id"):
                        self.message_editor(new_message)

            if self.loop_count == 10 or (
                (self.loop_count-10)*30 > self.message_cooldown
            ):
                self.send_to_discord(new_message)
                self.loop_count = 10

            time.sleep(30)
            self.last_player_array = [player_count, max_player_count]
            self.loop_count += 1


VIP().main_loop()

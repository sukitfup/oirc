import asyncio, re, ssl, time, base64
from botapi import api_request

MAX_MESSAGE_LENGTH = 450
RECON_INTERVAL = 5

class SimpleIRCBot:
    def __init__(self, interpreter=None):
        self.interpreter = interpreter
        self.server = None
        self.port = None
        self.channels = []
        self.nickname = None
        self.realname = None
        self.password = None
        self.trigger = None
        self.channels = None
        self.server = None
        self.port = None
        self.server_pass = None
        self.use_ssl = False
        self.use_sasl = True
        self.reader = None
        self.writer = None
        self.ssl_context = ssl.create_default_context()
        self.last_reply_time = 0
        self.semaphore = asyncio.Semaphore(1)  # Limit concurrency
        self.run = True
        self.authenticated = False

    async def initialize(self):
        print("Initializing bot with info from the API...")
        response = await api_request(endpoint='bot_info')
        bot_info = response.get('bot_info', {})

        self.nickname = bot_info.get('nickname', "")
        self.realname = bot_info.get('realname', "")
        self.password = bot_info.get('password', "")
        self.trigger = bot_info.get('trigger', "!")
        self.channels = bot_info.get('channels', [])
        
        network = bot_info.get('network', {})
        self.server = network.get('server', "")
        self.port = network.get('port', 0)
        self.use_ssl = network.get('use_ssl', False)
        self.server_pass = network.get('password', "")

    def should_reply(self):
        """Check if enough time has passed to send another reply."""
        current_time = time.time()
        if current_time - self.last_reply_time > 5:
            self.last_reply_time = current_time
            return True
        return False

    async def connect(self):
        print(f"Connecting to {self.server}:{self.port} with SSL: {self.use_ssl}")
        if self.use_ssl:
            self.reader, self.writer = await asyncio.open_connection(self.server, self.port, ssl=self.ssl_context)
        else:
            self.reader, self.writer = await asyncio.open_connection(self.server, self.port)
        if self.server_pass:
            await self.send_command(f"PASS {self.server_pass}")
        await self.send_command(f"NICK {self.nickname}")
        await self.send_command(f"USER {self.nickname} 0 * :{self.realname}")

    async def sasl_auth(self):
        # Wait for the server to acknowledge SASL capability
        current_time = time.time() 
        while time.time() - current_time < RECON_INTERVAL:
            line = await self.reader.readline()
            if not line:
                break
            line = line.decode('utf-8').strip()
            print(f"SASL Auth Received: {line}")
            
            if f"CAP {self.nickname} ACK :sasl" in line:
                await self.send_command("AUTHENTICATE PLAIN")
            elif "AUTHENTICATE :+" in line:
                # Prepare the Base64-encoded credentials
                auth_string = f"{self.nickname}\0{self.nickname}\0{self.password}"
                auth_base64 = base64.b64encode(auth_string.encode()).decode()
                
                await self.send_command(f"AUTHENTICATE {auth_base64}")
            elif "903" in line:  # Successful SASL authentication
                self.authenticated = True
                print("SASL Authentication successful!")
                await self.send_command("CAP END")
                break
            elif "904" in line or "905" in line:  # Failed SASL authentication
                print("SASL Authentication failed!")
                break


    async def send_command(self, command):
        print(f"Sending command: {command}")
        if self.writer is not None:
            self.writer.write((command + "\r\n").encode('utf-8'))
            await self.writer.drain()

    async def join_channel(self, channel):
        await self.send_command(f"JOIN {channel}")

    async def send_message(self, target, message):
        lines = message.splitlines()
        for line in lines:
            parts = [line[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(line), MAX_MESSAGE_LENGTH)]
            for part in parts:
                self.writer.write(f"PRIVMSG {target} :{part}\r\n".encode('utf-8'))
                await self.writer.drain()
                await asyncio.sleep(0.55)

    async def handle_messages(self):
        while self.run:
            line = await self.reader.readline()
            if not line:
                break
            line = line.decode('utf-8').strip()
            print(f"Received: {line}")
            self.last_ping_time = time.time()
            if line.startswith("PING"):
                await self.send_command(f"PONG {line.split()[1]}")
            elif '433' in line and not 'PRIVMSG' in line:
                if "Nickname is already in use" in line:
                    await self.handle_nickname_in_use()
            else:
                await self.process_message(line)

    async def handle_nickname_in_use(self):
        self.nickname = self.nickname + '_'
        await self.send_command(f"NICK {self.nickname}")
        await self.send_command(f"USER {self.nickname} 0 * :{self.realname}")

    async def generate_reply(self, message, target):
        try:
            reply = await self.interpreter.async_sync_chat(message)
            await self.send_message(target, reply)
        except Exception as e:
            await self.send_message(target, f"I broke: {e}")

    async def process_command(self, nickname, realname, hostmask, command, target):
        payload = {
                "X-Bot-User-Nick": nickname,
                "X-Bot-User-Real": realname,
                "X-Bot-User-Host": hostmask,
                "X-Bot-CMD": command
            }
        try:
            cmd = await api_request(endpoint='process_cmd', payload=payload)
            if 'notice' in cmd:
                notice = cmd.get('notice')
                print(f"Notice: {notice}")
            elif 'error' in cmd:
                error = cmd.get('error')
                print(f"Error: {error}")
            elif 'command' in cmd:
                bot_cmd = cmd.get('command')
                await self.send_command(bot_cmd)
        except Exception as e:
            print(f"Command processing error: {e}")

    async def process_message(self, line):
        if re.match(r'^:\S+ 001 \S+ :', line):
            print("Connection established.")

        elif re.match(r'^:\S+ 376 \S+ :', line) or re.match(r'^:\S+ 422 \S+ :', line):
            # End of MOTD or no MOTD
            if self.password:
                if self.use_sasl:
                    await self.send_command("CAP REQ :sasl")
                    await self.sasl_auth()
                if not self.authenticated:
                    await self.send_command(f"PRIVMSG NickServ IDENTIFY {self.password}")

            for channel in self.channels:
                await self.join_channel(channel)
        else:
            match = re.match(r'^:(\S+?)!(\S+?)@(\S+?) PRIVMSG (\S+?) :(.+)$', line)
            if match:
                sender_nick, sender_real, sender_host, target, message = match.groups()
                self.last_ping_time = time.time()
                
                if self.should_reply() and sender_nick.lower() != self.nickname.lower():
                    if target.lower() == self.nickname.lower():
                        target = sender_nick
                    
                    if message.startswith(self.trigger) or message.startswith('?'):
                        await self.process_command(sender_nick, sender_real, sender_host, message[1:], target)
                    elif message.lower().startswith(self.nickname.lower()):
                        message = re.sub(re.escape(self.nickname), '', message, flags=re.IGNORECASE, count=1).strip()
                        async with self.semaphore:
                            asyncio.create_task(self.generate_reply(message, target))


    async def disconnect(self):
        if self.reader:
            self.reader = None
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
        
    async def start(self):
        await self.initialize()
        while self.run:
            print(f"Attempting to connect to {self.server}:{self.port}...")
            try:
                await self.connect()
                await self.handle_messages()
            except Exception as e:
                print(f"Connection error: {e}")
            finally:
                self.authenticated = False
                await self.disconnect()
                print(f"Reconnecting in {RECON_INTERVAL} seconds...")
                await asyncio.sleep(RECON_INTERVAL)
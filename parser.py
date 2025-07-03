import re
from datetime import datetime

class ZelleMessageParser:
    '''
    Parses Zelle text messages for poker-related transactions.
    '''
    KEYWORDS = ['poker', 'buy-in', 'buyin', 'game', 'chips']
    PATTERN = re.compile(
        r"From:\s*(?P<sender>.*?)\s+"
        r"Amount:\s*\$(?P<amount>[\d\.]+)\s+"
        r"Date:\s*(?P<date>\d{4}-\d{2}-\d{2})\s+"
        r"Time:\s*(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"Ref:\s*(?P<ref>\w+)"
    )

    @classmethod
    def is_poker_message(cls, text):
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cls.KEYWORDS)

    @classmethod
    def parse(cls, text):
        if not cls.is_poker_message(text):
            return None
        match = cls.PATTERN.search(text)
        if not match:
            return None
        data = match.groupdict()
        dt = datetime.strptime(data['date'] + ' ' + data['time'], '%Y-%m-%d %H:%M:%S')
        return {
            'sender': data['sender'].strip(),
            'amount': float(data['amount']),
            'datetime': dt,
            'ref': data['ref']
        }

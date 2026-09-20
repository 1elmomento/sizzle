"""Builds a showcase account (invented people, groups, channels, two years of messages) for the promo video.

Nothing here comes from a real account: names, chats and messages are all made up.
"""

import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram_manager.core.models import Account, ChatInfo, ChatKind, ChatSyncState, MessageInfo
from telegram_manager.core.storage import Storage

OUT = Path(sys.argv[1])
rng = random.Random(11)
NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
ACCOUNT = Account(1, "Sam Carter", "samcarter", None)

# name, messages per active day at peak, shape
PEOPLE = [
    ("Lena Park", 34, "steady"), ("Omid Karimi", 22, "rising"), ("Maya Chen", 18, "fading"),
    ("Noah Fischer", 15, "steady"), ("Sara Ahmadi", 14, "new"), ("Jonas Weber", 12, "fading"),
    ("Aria Novak", 11, "rising"), ("Daniel Brooks", 10, "steady"), ("Nika Rahimi", 9, "bursty"),
    ("Theo Martin", 8, "quiet"), ("Chloe Dubois", 8, "steady"), ("Kian Moradi", 7, "rising"),
    ("Emma Lindqvist", 7, "fading"), ("Lucas Rossi", 6, "steady"), ("Yara Haddad", 6, "bursty"),
    ("Ben Okafor", 5, "quiet"), ("Mina Sato", 5, "steady"), ("Arman Tehrani", 5, "fading"),
    ("Olivia Grant", 4, "new"), ("Felix Wagner", 4, "steady"), ("Zoe Adams", 4, "rising"),
    ("Reza Farahani", 3, "quiet"), ("Hana Kim", 3, "steady"), ("Leo Costa", 3, "fading"),
    ("Isla Murphy", 3, "bursty"), ("Mateo Silva", 2, "steady"), ("Nora Berg", 2, "quiet"),
    ("Dara Jafari", 2, "rising"), ("Ethan Cole", 2, "steady"), ("Ava Laurent", 2, "fading"),
    ("Sina Kazemi", 1.5, "steady"), ("Ruby Hayes", 1.5, "quiet"), ("Milan Horvat", 1.2, "steady"),
    ("Tara Nasiri", 1.2, "new"), ("Oscar Lund", 1, "fading"), ("Elena Petrova", 1, "steady"),
    ("Parsa Rezaei", 1, "bursty"), ("Julia Wolf", 0.8, "steady"), ("Adam Novak", 0.6, "quiet"),
    ("Layla Aziz", 0.6, "steady"), ("Victor Hugo Lima", 0.5, "fading"), ("Mom", 6, "steady"),
]
GROUPS = [
    ("Family ❤️", 30, False), ("Design Crew", 22, False), ("Startup Founders", 40, False),
    ("Weekend Hiking", 8, False), ("Book Club 📚", 6, False), ("Class of 2019", 0.4, True),
    ("Apartment 4B", 3, False), ("Python Tehran", 25, False), ("Product Managers", 18, False),
    ("Crypto Talk 🚀", 45, True), ("Old Office Crew", 0.2, True), ("Football Sundays ⚽", 5, False),
    ("Photography Club", 2, True), ("Wedding Planning 💍", 0.1, True), ("Language Exchange", 4, True),
    ("Remote Workers", 12, False), ("UX Research", 7, False), ("Travel Buddies ✈️", 1, True),
    ("Gaming Night 🎮", 9, False), ("Neighbours", 2, False), ("Hackathon 2024", 0.05, True),
    ("Design Systems", 6, False), ("کلاس زبان", 1, True), ("Night Owls", 3, False),
    ("Cooking Recipes", 1, True), ("Parents of 3B", 10, False), ("Indie Makers", 14, False),
    ("Fitness Challenge", 0.1, True), ("Jazz Lovers", 1, False), ("Moving Sale", 0.05, True),
]
CHANNELS = [
    ("Tech Digest", "techdigest", 6), ("Daily News", "dailynews", 12), ("Design Inspiration", "designinspo", 3),
    ("Product Hunt Daily", "phdaily", 4), ("Space & Science", "spacesci", 2), ("Morning Briefing", "briefing", 1),
    ("Dev Tips", "devtips", 3), ("Crypto Signals", "signals", 20), ("Travel Deals", "traveldeals", 5),
    ("Photography Weekly", "photoweekly", 0.3), ("Startup Stories", "startupstories", 1.5),
    ("AI Research Notes", "ainotes", 2.5), ("Book Quotes", "bookquotes", 1), ("Memes Central", "memes", 15),
    ("Weather Alerts", "weather", 2), ("Football Live", "footballlive", 8), ("Music Releases", "newmusic", 2),
    ("Movie Night", "movienight", 0.5), ("Recipes Daily", "recipes", 1), ("Language Bites", "langbites", 0.2),
    ("Minimal Living", "minimal", 0.1), ("Retro Games", "retrogames", 0.2), ("Architecture Now", "archnow", 0.8),
    ("Productivity Hacks", "productivity", 1), ("Open Source Weekly", "osweekly", 0.6),
    ("Podcast Picks", "podcasts", 0.3), ("Urban Sketchers", "sketchers", 0.1), ("Deal Hunters", "deals", 6),
    ("Health Facts", "healthfacts", 0.7), ("Night Sky", "nightsky", 0.15),
]
BOTS = ["Weather Bot", "Translate Bot", "Remind Me Bot", "Polls Bot", "File Converter Bot", "Music Finder Bot"]

CHAT_LINES = [
    "are you free tonight?", "haha exactly 😂", "sending you the photos now", "can we move the meeting to 4?",
    "just landed!", "did you see the news?", "ok sounds good", "thank you so much ❤️", "on my way",
    "let's plan the trip for next month", "what time works for you?", "I'll call you later",
    "the trip photos are amazing", "happy birthday!! 🎉", "miss you", "good morning ☀️", "that's hilarious",
    "can you send me the file?", "running 10 min late sorry", "dinner on Friday?", "love this song",
    "we should book the trip tickets soon", "how was the interview?", "congrats!!", "see you tomorrow",
    "the meeting notes are in the doc", "I'm so tired today", "coffee?", "lol", "same here",
    "check this out", "you won't believe what happened", "sure thing", "let me know when you're home",
]
POSTS = [
    "The 10 best productivity apps of the year, tested for a month each. Our favourite surprised us.",
    "Breaking: new climate agreement reached after two weeks of talks. Here's what changes next year.",
    "A quiet little design detail: why the best buttons have 4 states, not 2.",
    "Launch of the day: an open-source tool that turns screenshots into editable UI mockups.",
    "Tonight: the Perseid meteor shower peaks. Best viewing is after midnight, away from city lights.",
    "Your morning briefing — markets calm, a big week for tech earnings, and rain in the afternoon.",
    "Tip: git switch - takes you back to the previous branch, just like cd -.",
    "Weekend trip idea: 3 days in Lisbon on a budget, with the best viewpoints and pastel de nata spots.",
    "New research shows small language models can match big ones on narrow tasks with the right data.",
    "\"A reader lives a thousand lives before he dies.\" — George R.R. Martin",
    "Match report: a last-minute goal seals the derby 2–1 in front of a record crowd.",
    "New album out today: 11 tracks, recorded live in one take over a single weekend.",
    "Architecture of the week: a timber library that stays cool all summer without air conditioning.",
    "How a two-person startup grew to 10,000 customers without spending a dollar on ads.",
    "Recipe: one-pan lemon garlic pasta, ready in 15 minutes.",
    "The easiest habit that actually stuck for us: a 5-minute plan for tomorrow, every evening.",
]


CHANNEL_POSTS = {
    "Tech Digest": ["The 10 best productivity apps of the year, tested for a month each. Our favourite surprised us.",
                    "A new laptop chip claims 20 hours of battery life. We ran our own tests this week."],
    "Daily News": ["New climate agreement reached after two weeks of talks. Here's what changes next year.",
                   "City council approves the new bike lane network, with construction starting in spring."],
    "Design Inspiration": ["A quiet little design detail: why the best buttons have 4 states, not 2.",
                           "Colour palette of the day: deep navy, sky blue and a single warm accent."],
    "Product Hunt Daily": ["Launch of the day: an open-source tool that turns screenshots into editable UI mockups.",
                           "Top 5 launches this week, from a pocket-sized synth to a calmer email client."],
    "Space & Science": ["Tonight the Perseid meteor shower peaks. Best viewing is after midnight, away from city lights."],
    "Morning Briefing": ["Your morning briefing: markets calm, a big week for tech earnings, and rain in the afternoon."],
    "Dev Tips": ["Tip: git switch - takes you back to the previous branch, just like cd -.",
                 "Tip: python -m http.server turns any folder into a website in one second."],
    "Crypto Signals": ["Market update: volatility is low this week. As always, no financial advice here.",
                       "Weekly recap: the three biggest moves and what drove them."],
    "Travel Deals": ["Weekend in Lisbon from 89€ return. Best viewpoints and pastel de nata spots in the thread.",
                     "Autumn sale: city breaks across Europe at half price until Sunday."],
    "Photography Weekly": ["Golden hour cheat sheet: shoot 20 minutes before sunset, with the sun at your side."],
    "Startup Stories": ["How a two-person startup grew to 10,000 customers without spending a dollar on ads."],
    "AI Research Notes": ["New research: small language models can match big ones on narrow tasks with the right data."],
    "Book Quotes": ["“A reader lives a thousand lives before he dies.” George R.R. Martin"],
    "Memes Central": ["Me opening Telegram after one day offline: 4,812 unread messages. Me: closes app.",
                      "When the group chat plans a trip and nobody books anything."],
    "Weather Alerts": ["Heavy rain expected from 3 pm to 9 pm. Take an umbrella and allow extra travel time."],
    "Football Live": ["Match report: a last-minute goal seals the derby 2–1 in front of a record crowd.",
                      "Team news: the captain is back in training and could start on Saturday."],
    "Music Releases": ["New album out today: 11 tracks, recorded live in one take over a single weekend."],
    "Movie Night": ["This week's pick: a slow, beautiful sci-fi film about a lighthouse keeper on Mars."],
    "Recipes Daily": ["One-pan lemon garlic pasta, ready in 15 minutes. Full recipe inside."],
    "Language Bites": ["Word of the day: 'hygge', the cosy feeling of candles, blankets and good company."],
    "Minimal Living": ["The one-in, one-out rule: every new thing replaces an old one."],
    "Retro Games": ["30 years ago today, a certain plumber first jumped into 3D."],
    "Architecture Now": ["A timber library that stays cool all summer without air conditioning."],
    "Productivity Hacks": ["The habit that finally stuck for us: a 5-minute plan for tomorrow, every evening."],
    "Open Source Weekly": ["This week in open source: a new release of the terminal everyone's switching to."],
    "Podcast Picks": ["Three episodes for your commute, all under 30 minutes."],
    "Urban Sketchers": ["Sunday sketch walk: meet at the old harbour at 10, bring any pen you like."],
    "Deal Hunters": ["Noise-cancelling headphones at their lowest price ever, today only.",
                     "Deal: 3 months of a popular music service for free for new users."],
    "Health Facts": ["A 10-minute walk after meals noticeably lowers blood sugar spikes."],
    "Night Sky": ["Saturn is at its brightest this month. Look south-east after 10 pm."],
}


def shape(kind: str, days_ago: int, seed: float) -> float:
    if kind == "rising":
        return 0.15 + 1.2 * max(0.0, 1 - days_ago / 260) ** 1.4
    if kind == "fading":
        return 0.12 + 1.1 * min(1.0, days_ago / 300) ** 1.2
    if kind == "quiet":
        return 0.0 if days_ago < 420 else 0.8
    if kind == "new":
        return 0.0 if days_ago > 150 else 1.0
    if kind == "bursty":
        return 0.25 + 2.2 * max(0.0, math.sin(days_ago / 23 + seed)) ** 8
    return 0.75 + 0.25 * math.sin(days_ago / 40 + seed)


def season(day: datetime) -> float:
    """A livelier December, a calmer late summer: makes the year's curve breathe."""
    doy = day.timetuple().tm_yday
    return 1 + 0.35 * math.exp(-((doy - 355) % 365 - 0) ** 2 / 400) + 0.2 * math.sin(doy / 58)


HOURS = [0.6, 0.4, 0.2, 0.1, 0.05, 0.05, 0.1, 0.3, 0.6, 0.8, 0.9, 1.0, 1.2, 1.1, 0.9, 0.9, 1.0, 1.1, 1.3, 1.5, 1.7, 1.9, 1.8, 1.2]


def hour() -> int:
    return rng.choices(range(24), weights=HOURS)[0]


def poisson(rate: float) -> int:
    if rate <= 0:
        return 0
    if rate < 20:
        limit, k, p = math.exp(-rate), 0, 1.0
        while True:
            p *= rng.random()
            if p <= limit:
                return k
            k += 1
    return max(0, round(rng.gauss(rate, math.sqrt(rate))))


def main() -> None:
    storage = Storage(OUT, ACCOUNT.id)
    storage.save_account(ACCOUNT)
    chats: list[ChatInfo] = []
    messages: list[MessageInfo] = []
    states: list[ChatSyncState] = []

    def add_chat(chat_id, title, kind, dated: list[tuple[datetime, bool, str, str]], **extra):
        dated.sort()
        batch = []
        for i, (when, out, sender, text) in enumerate(dated, start=1):
            batch.append(MessageInfo(chat_id, i, when, out=out, sender_id=ACCOUNT.id if out else chat_id,
                                     sender_name="Sam Carter" if out else sender, text=text))
        messages.extend(batch)
        last = batch[-1] if batch else None
        chats.append(ChatInfo(
            chat_id, title, kind, last_message=last.text if last else "", last_date=last.date if last else NOW,
            top_message_id=len(batch), last_sender="You" if last and last.out else (last.sender_name if last else ""),
            **extra,
        ))
        states.append(ChatSyncState(chat_id, 1 if batch else 0, len(batch), complete=True, total=len(batch)))

    for index, (name, rate, kind) in enumerate(PEOPLE):
        seed = rng.random() * 6
        share = rng.uniform(0.42, 0.6)
        dated = []
        for days_ago in range(0, 730):
            day = NOW - timedelta(days=days_ago)
            weekend = 1.25 if day.weekday() >= 5 else 1.0
            for _ in range(poisson(rate * shape(kind, days_ago, seed) * season(day) * weekend * rng.uniform(0.3, 1.4))):
                when = day.replace(hour=hour(), minute=rng.randrange(60))
                if when > NOW:
                    when = NOW - timedelta(minutes=rng.randrange(1, 300))
                dated.append((when, rng.random() < share, name, rng.choice(CHAT_LINES)))
        unread = rng.choice([0, 0, 0, 1, 2, 5]) if index < 20 else 0
        add_chat(1000 + index, name, ChatKind.PRIVATE, dated, unread_count=unread,
                 muted=name in ("Reza Farahani", "Adam Novak", "Victor Hugo Lima"), pinned=name in ("Lena Park", "Mom"))

    for index, (name, rate, inactive) in enumerate(GROUPS):
        members = rng.sample([p[0] for p in PEOPLE], 6)
        dated = []
        for days_ago in range(0, 730, 1):
            if inactive and days_ago < 200:
                continue
            day = NOW - timedelta(days=days_ago)
            for _ in range(poisson(rate * rng.uniform(0.2, 1.2))):
                when = day.replace(hour=hour(), minute=rng.randrange(60))
                if when > NOW:
                    when = NOW - timedelta(minutes=rng.randrange(1, 300))
                out = rng.random() < (0.02 if name in ("Crypto Talk 🚀", "Class of 2019", "Hackathon 2024", "Moving Sale", "Photography Club") else 0.12)
                dated.append((when, out, rng.choice(members), rng.choice(CHAT_LINES)))
        unread = 0 if inactive else rng.choice([0, 3, 12, 48, 120, 7])
        add_chat(-100 - index, name, ChatKind.GROUP, dated, unread_count=unread,
                 muted=name in ("Crypto Talk 🚀", "Parents of 3B", "Class of 2019", "Neighbours", "Remote Workers"))

    for index, (name, username, rate) in enumerate(CHANNELS):
        dated = []
        for days_ago in range(0, 365):
            day = NOW - timedelta(days=days_ago)
            for _ in range(poisson(rate * rng.uniform(0.5, 1.3))):
                when = day.replace(hour=rng.choice([7, 8, 9, 12, 15, 18, 20]), minute=rng.randrange(60))
                if when > NOW:
                    when = NOW - timedelta(minutes=rng.randrange(1, 500))
                dated.append((when, False, name, rng.choice(CHANNEL_POSTS.get(name, POSTS))))
        unread = rng.choice([0, 14, 86, 230, 1204, 9, 57]) if rate > 1 else 0
        add_chat(-1000000 - index, name, ChatKind.CHANNEL, dated, username=username, unread_count=unread,
                 muted=rate > 4 or name in ("Memes Central",))

    for index, name in enumerate(BOTS):
        dated = [(NOW - timedelta(days=rng.randrange(1, 300), minutes=rng.randrange(600)), False, name, "Done ✅")
                 for _ in range(rng.randrange(3, 30))]
        add_chat(900000 + index, name, ChatKind.BOT, dated)

    chats.sort(key=lambda c: (not c.pinned, -(c.last_date.timestamp())))
    storage.save_messages(messages)
    for state in states:
        storage.save_sync_state(state)
    storage.save_chat_snapshot(chats, synced_at=NOW - timedelta(minutes=2))

    # A little history in the activity log.
    for action, picked in (("mute", [c for c in chats if c.kind is ChatKind.CHANNEL][:6]),
                           ("leave", [c for c in chats if c.kind is ChatKind.GROUP][-4:]),
                           ("mark_read", [c for c in chats if c.kind is ChatKind.CHANNEL][6:18])):
        activity = storage.create_activity(action, [(c.id, c.title) for c in picked])
        for c in picked:
            storage.set_activity_item(activity, c.id, "done")
        storage.finish_activity(activity, "done")
    print(len(chats), "chats,", len(messages), "messages")


main()

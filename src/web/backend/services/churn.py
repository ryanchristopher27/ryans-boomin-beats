"""What's new vs what's a staple (Profile): compare top artists and tracks across
Spotify's three time ranges. Ranks are 1-based; a missing rank means the item
isn't in that range's top 50."""

LIST_LEN = 6
# "Rising": at least this many places higher over 4 weeks than over 6 months.
RISE_BY = 10


def compare(short: list[dict], medium: list[dict], long: list[dict]) -> dict:
    """Each list is the range's top items in order, as dicts with an `id`."""
    rank = lambda items: {it['id']: i + 1 for i, it in enumerate(items)}  # noqa: E731
    s, m, l = rank(short), rank(medium), rank(long)
    items = {it['id']: it for it in [*long, *medium, *short]}
    with_ranks = lambda i: {**items[i], 'ranks': {'short': s.get(i), 'medium': m.get(i), 'long': l.get(i)}}  # noqa: E731

    new = [i for i in s if i not in m and i not in l]
    staples = sorted((i for i in s if i in m and i in l), key=lambda i: s[i] + m[i] + l[i])
    rising = sorted((i for i in s if i in m and m[i] - s[i] >= RISE_BY), key=lambda i: s[i] - m[i])
    fading = [i for i in l if i not in s]
    return {k: [with_ranks(i) for i in v[:LIST_LEN]] for k, v in
            {'new': new, 'staples': staples, 'rising': rising, 'fading': fading}.items()}

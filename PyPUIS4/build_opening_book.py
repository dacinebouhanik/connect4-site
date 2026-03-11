from db import lister_parties
import json

MAX_DEPTH = 12

book = {}

parties = lister_parties()

for game in parties:

    coups = game[5]

    for i in range(min(MAX_DEPTH, len(coups) - 1)):

        prefix = coups[:i]
        next_move = coups[i]

        if prefix not in book:
            book[prefix] = {}

        if next_move not in book[prefix]:
            book[prefix][next_move] = 0

        book[prefix][next_move] += 1


opening_book = {}

for position, moves in book.items():

    best_move = max(moves, key=moves.get)

    opening_book[position] = best_move


with open("opening_book.json", "w") as f:
    json.dump(opening_book, f)

print("Opening book créé")
print("Positions:", len(opening_book))
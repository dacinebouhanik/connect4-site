from db import test_connexion, lister_parties

print("Connexion :", test_connexion())
print("Parties en base :")

for p in lister_parties():
    print(p)

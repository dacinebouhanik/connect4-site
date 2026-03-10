from scrape_partie_bga import scraper_partie_bga

table_id = "816518007"   # mets un vrai id BGA ici

coups = scraper_partie_bga(table_id)

print("Coups récupérés :", coups)
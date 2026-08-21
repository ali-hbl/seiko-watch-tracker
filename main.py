import os
import re
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

load_dotenv()

# =======================================================
# COMPOSANTS : OUTILS ET LLM
# =======================================================
llm_groq = LLM(
    model="groq/qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY"),
    max_completion_tokens=800 # Sécurité anti-quota
)

recherche_google = SerperDevTool()

# =======================================================
# COMPOSANTS : AGENT ET MISSION (Retour au naturel !)
# =======================================================
chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver 3 offres pour la montre Seiko SBTR027 sur internet.",
    backstory="""Tu es un expert en montres japonaises (JDM). Ton client cherche la Seiko SBTR027.
    RÈGLE N°1 : N'utilise JAMAIS les balises <think>.
    RÈGLE N°2 : Cherche via Google sur des sites comme Chrono24, eBay ou Sakura Watches.
    Les prix se trouvent très souvent dans les extraits (snippets).""",
    verbose=True, 
    allow_delegation=False,
    max_iter=1, # 1 seule recherche pour protéger le quota
    tools=[recherche_google],
    llm=llm_groq 
)

mission_seiko = Task(
    description="""
    Trouve 3 offres actuelles pour la Seiko SBTR027.
    Rédige un rapport final clair avec le nom de la boutique, le prix (en euros ou USD) et le lien.
    """,
    expected_output="Un rapport final structuré, clair et net, EXCLUSIVEMENT EN FRANÇAIS.",
    agent=chasseur_montres
)

equipe = Crew(
    agents=[chasseur_montres],
    tasks=[mission_seiko],
    process=Process.sequential, 
    verbose=True
)

# =======================================================
# ENVOI TELEGRAM & ANALYSE DU TEXTE
# =======================================================
def envoyer_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(os.getenv("TELEGRAM_CHAT_ID")).strip()

    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Envoi en texte brut (sans markdown qui bug sur Telegram)
    requests.post(url, json={"chat_id": chat_id, "text": message})

if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    rapport_texte = str(resultat_final)
    
    # 1. Nettoyage du "think"
    if "</think>" in rapport_texte:
        rapport_nettoye = rapport_texte.split("</think>")[-1].strip()
    else:
        rapport_nettoye = re.sub(r'<think>.*', '', rapport_texte, flags=re.DOTALL).strip()
    
    if not rapport_nettoye:
        rapport_nettoye = rapport_texte
        
    # 2. Nettoyage des astérisques pour Telegram
    rapport_nettoye = rapport_nettoye.replace("**", "").replace("*", "-")
    
    # ==========================================================
    # 3. LE SCANNER PYTHON (Trouve le prix sans forcer l'IA)
    # ==========================================================
    
    # Python cherche tous les groupes de 2 ou 3 chiffres dans le texte (ex: 135, 99, 240)
    nombres_trouves = re.findall(r'\b(\d{2,3})\b', rapport_nettoye)
    
    # On filtre pour ne garder que les nombres plausibles pour le prix de cette montre (entre 50 et 400)
    prix_plausibles = [int(n) for n in nombres_trouves if 50 <= int(n) <= 400]
    
    if prix_plausibles:
        # On prend mathématiquement le plus petit nombre trouvé
        prix_minimum = min(prix_plausibles)
        print(f"Prix le plus bas détecté dans le texte : {prix_minimum}")
        
        # TEST : J'ai mis le seuil à 200 temporairement pour forcer l'envoi sur votre téléphone !
        if prix_minimum < 200: 
            print("Prix sous le seuil ! Envoi de l'alerte Telegram...")
            titre = "🚨 ALERTE PRIX : SEIKO SBTR027 🚨\n\n"
            envoyer_telegram(titre + rapport_nettoye[:3900])
        else:
            print(f"Le prix le plus bas est de {prix_minimum}. C'est trop cher, pas de message !")
            
    else:
        print("Aucun prix détecté, envoi du rapport par sécurité.")
        titre = "⌚️ RAPPORT SEIKO SBTR027 ⌚️\n\n"
        envoyer_telegram(titre + rapport_nettoye[:3900])
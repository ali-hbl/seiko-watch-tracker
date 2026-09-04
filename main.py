import os
import re
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

os.environ["LITELLM_DROP_PARAMS"] = "True"
load_dotenv()

# =======================================================
# COMPOSANTS : OUTILS ET LLM
# =======================================================
llm_groq = LLM(
    model="groq/qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY"),
    max_completion_tokens=2000
)

recherche_google = SerperDevTool()

# =======================================================
# COMPOSANTS : AGENT ET MISSION
# =======================================================
chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver 3 offres pour la montre Seiko SBTR027 sur internet.",
    backstory="""Tu es un expert en montres japonaises (JDM). Ton client cherche la Seiko SBTR027.
    RÈGLE N°1 : Cherche via Google sur des sites comme Chrono24, eBay ou Sakura Watches.
    RÈGLE N°2 : Donne les prix exacts trouvés en euros ou dollars dans ton rapport final.""",
    verbose=True, 
    allow_delegation=False,
    max_iter=1, # On garde 1 seule recherche pour protéger le quota 
    tools=[recherche_google],
    llm=llm_groq 
)

mission_seiko = Task(
    description="""
    Trouve 3 offres actuelles pour la Seiko SBTR027.
    Rédige un rapport final clair avec le nom de la boutique, le prix, la disponibilité et le lien.
    NE DONNE QUE LE RAPPORT FINAL EN FRANÇAIS.
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
    requests.post(url, json={"chat_id": chat_id, "text": message})

if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    rapport_texte = str(resultat_final)
    
    # 1. Nettoyage du "think"
    if "</think>" in rapport_texte:
        rapport_nettoye = rapport_texte.split("</think>")[-1].strip()
    else:
        rapport_nettoye = re.sub(r'<think>.*', '', rapport_texte, flags=re.DOTALL).strip()
    
    # SÉCURITÉ : Si l'IA n'a pas pu terminer, on n'envoie PAS son brouillon
    if not rapport_nettoye:
        rapport_nettoye = "⚠️ L'agent a été interrompu avant de pouvoir terminer son rapport. Pas de résultat aujourd'hui."
        
    # 2. Nettoyage des astérisques pour Telegram
    rapport_nettoye = rapport_nettoye.replace("**", "").replace("*", "-")
    
    # 3. LE SCANNER PYTHON (Trouve le prix sans forcer l'IA)
    nombres_trouves = re.findall(r'\b(\d{2,3})\b', rapport_nettoye)
    prix_plausibles = [int(n) for n in nombres_trouves if 50 <= int(n) <= 400]
    
    if prix_plausibles:
        prix_minimum = min(prix_plausibles)
        print(f"Prix le plus bas détecté dans le texte : {prix_minimum}")
        
        if prix_minimum < 120: 
            print("Prix sous le seuil ! Envoi de l'alerte Telegram...")
            titre = "🚨 ALERTE PRIX : SEIKO SBTR027 🚨\n\n"
            envoyer_telegram(titre + rapport_nettoye[:3900])
        else:
            print(f"Le prix le plus bas est de {prix_minimum}. C'est trop cher, pas de message !")
            
    else:
        print("Aucun prix détecté, envoi du rapport par sécurité.")
        titre = "⌚️ RAPPORT SEIKO SBTR027 ⌚️\n\n"
        envoyer_telegram(titre + rapport_nettoye[:3900])
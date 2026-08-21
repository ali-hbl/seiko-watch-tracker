import os
import re
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool # L'outil professionnel Google Search

load_dotenv()

# =======================================================
# COMPOSANTS : OUTILS ET LLM
# =======================================================
llm_groq = LLM(
    model="groq/qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY")
)

# On active l'outil pro (qui va automatiquement chercher la SERPER_API_KEY dans l'environnement)
recherche_google = SerperDevTool()

# =======================================================
# COMPOSANTS : AGENT ET MISSION
# =======================================================
chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver 3 offres pour la montre Seiko SBTR027 sur internet.",
    backstory="""Tu es un expert en montres japonaises (JDM). Ton client cherche la Seiko SBTR027.
    RÈGLE ABSOLUE N°1 : N'utilise JAMAIS les balises <think>.
    RÈGLE ABSOLUE N°2 : Utilise ton outil de recherche Google pour trouver le prix de la montre sur des sites comme Chrono24, eBay, ou Sakura Watches. 
    Les prix se trouvent très souvent dans les extraits (snippets) des résultats de recherche. Lis-les attentivement !""",
    verbose=True, 
    allow_delegation=False,
    max_iter=3, 
    tools=[recherche_google], # L'agent est équipé de vraies lunettes Google
    llm=llm_groq 
)

mission_seiko = Task(
    description="""
    Trouve 3 offres actuelles pour acheter la montre Seiko SBTR027. 
    Pour chaque offre, donne : le nom de la boutique, le prix, la disponibilité, et le lien URL.
    """,
    expected_output="Un rapport final structuré en Markdown, EXCLUSIVEMENT EN FRANÇAIS. Donne un résultat net et direct.",
    agent=chasseur_montres
)

equipe = Crew(
    agents=[chasseur_montres],
    tasks=[mission_seiko],
    process=Process.sequential, 
    verbose=True
)

# =======================================================
# ENVOI TELEGRAM & NETTOYAGE
# =======================================================
def envoyer_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(os.getenv("TELEGRAM_CHAT_ID")).strip()

    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).raise_for_status()
    except requests.exceptions.HTTPError:
        requests.post(url, json={"chat_id": chat_id, "text": message})

if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    rapport_texte = str(resultat_final)
    
    # Nettoyage ultra-sécurisé du "think"
    if "</think>" in rapport_texte:
        rapport_nettoye = rapport_texte.split("</think>")[-1].strip()
    else:
        rapport_nettoye = re.sub(r'<think>.*', '', rapport_texte, flags=re.DOTALL).strip()
    
    if not rapport_nettoye:
        rapport_nettoye = rapport_texte # Secours absolu si tout échoue
        
    titre = "⌚️ **RAPPORT QUOTIDIEN SEIKO SBTR027** ⌚️\n\n"
    texte_a_envoyer = titre + rapport_nettoye[:3900] 
    
    envoyer_telegram(texte_a_envoyer)
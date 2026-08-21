import os
import requests
import re # Pour utiliser les regex
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from crewai_tools import ScrapeWebsiteTool # L'outil de lecture de sites web officiel de CrewAI

load_dotenv()

# =======================================================
# COMPOSANTS : OUTILS ET LLM
# =======================================================
llm_groq = LLM(
    model="groq/qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY")
)

@tool("Recherche_Web_DuckDuckGo")
def recherche_web(requete: str) -> str:
    """Cherche des liens et des pages web sur internet."""
    try:
        results = DDGS().text(requete, max_results=3)
        if not results:
            return "Aucun résultat."
        return "\n\n---\n\n".join([f"Titre : {r['title']}\nLien : {r['href']}" for r in results])
    except Exception as e:
        return f"Erreur : {str(e)}"

# On instancie l'outil qui permet de lire le contenu d'un site web
outil_lecture_site = ScrapeWebsiteTool()

# =======================================================
# COMPOSANTS : AGENT ET MISSION
# =======================================================
chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver la montre Seiko SBTR027 en stock au meilleur prix sur internet.",
    backstory="""Tu es un expert en montres japonaises (JDM). Ton client cherche absolument à acheter la Seiko SBTR027 (C'est un chronographe cadran gris-bleu/glacier qui EXISTE bel et bien, ne dis JAMAIS le contraire). 
    Si ta première recherche échoue, essaie des termes très précis comme : 'Seiko SBTR027 Sakura Watches', 'Seiko SBTR027 eBay', ou 'Seiko SBTR027 Discovery Japan'. 
    Trouve les boutiques, lis les prix et synthétise l'info.""",
    verbose=True, 
    allow_delegation=False,
    max_iter=4, 
    tools=[recherche_web, outil_lecture_site],
    llm=llm_groq 
)

mission_seiko = Task(
    description="""
    Trouve 3 offres actuelles et fiables pour acheter la montre Seiko SBTR027. 
    Pour chaque offre, tu DOIS fournir :
    1. Le nom de la boutique.
    2. Le prix affiché (avec la devise).
    3. La disponibilité (En stock ou Rupture).
    4. Le lien URL direct vers la montre.
    Si tu ne trouves pas l'info exacte, dis-le clairement.
    """,
    expected_output="Un rapport final structuré en Markdown, EXCLUSIVEMENT EN FRANÇAIS. Ne fournis aucun détail sur ta méthode de recherche, donne juste le résultat net et concis.",
    agent=chasseur_montres
)

equipe = Crew(
    agents=[chasseur_montres],
    tasks=[mission_seiko],
    process=Process.sequential, 
    verbose=True
)

# =======================================================
# COMPOSANT : ENVOI TELEGRAM SÉCURISÉ
# =======================================================
def envoyer_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(os.getenv("TELEGRAM_CHAT_ID")).strip()
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message})
        except Exception:
            pass

# =======================================================
# EXECUTION
# =======================================================
if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    rapport_texte = str(resultat_final)
    
    # S'il a fini de penser, on prend tout ce qu'il y a APRES la balise
    if "</think>" in rapport_texte:
        rapport_nettoye = rapport_texte.split("</think>")[-1].strip()
    else:
        # S'il a été coupé en pleine réflexion
        rapport_nettoye = re.sub(r'<think>.*', '', rapport_texte, flags=re.DOTALL).strip()
        
        if not rapport_nettoye:
            rapport_nettoye = "⚠️ L'agent n'a pas trouvé de résultats concluants aujourd'hui ou a été interrompu."

    titre = "⌚️ **RAPPORT QUOTIDIEN SEIKO SBTR027** ⌚️\n\n"
    texte_a_envoyer = titre + rapport_nettoye[:3900] 
    
    envoyer_telegram(texte_a_envoyer)
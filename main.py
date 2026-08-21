import os
import requests
import re # Pour utiliser les regex
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

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
        results = DDGS().text(requete, max_results=4)
        if not results:
            return "Aucun résultat pour cette recherche précise."
        
        # Force l'extraction du "body" (le texte sous le lien bleu Google/DuckDuckGo)
        return "\n\n---\n\n".join([f"Titre : {r['title']}\nExtrait (Où se trouve peut-être le prix) : {r['body']}\nLien : {r['href']}" for r in results])
    except Exception as e:
        return f"Erreur de recherche : {str(e)}"

# =======================================================
# COMPOSANTS : AGENT ET MISSION
# =======================================================
chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver le prix de la Seiko SBTR027 uniquement en lisant les extraits de recherche.",
    backstory="""Tu es un expert en montres JDM. Ton client veut la Seiko SBTR027.
    RÈGLE ABSOLUE N°1 : Tu NE DOIS JAMAIS utiliser les balises <think>. Réponds TOUJOURS directement.
    RÈGLE ABSOLUE N°2 : Les sites e-commerce bloquent les robots. Tu ne peux pas visiter les pages.
    Ta stratégie : Fais des recherches (ex: 'Seiko SBTR027 price Sakura Watches' ou 'SBTR027 Chrono24 USD') et déduis le prix directement depuis l''Extrait' des résultats de recherche. Ne cherche pas la perfection, donne les indices que tu trouves.""",
    verbose=True, 
    allow_delegation=False,
    max_iter=3, 
    tools=[recherche_web], # On ne lui donne QUE cet outil !
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
# =======================================================
# EXECUTION
# =======================================================
if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    
    # On prend le résultat directement
    rapport_texte = str(resultat_final)
    
    # On s'assure juste de nettoyer au cas où l'IA désobéit un tout petit peu
    rapport_nettoye = re.sub(r'<think>.*?</think>', '', rapport_texte, flags=re.DOTALL).strip()
    
    titre = "⌚️ **RAPPORT QUOTIDIEN SEIKO SBTR027** ⌚️\n\n"
    texte_a_envoyer = titre + rapport_nettoye[:3900] 
    
    envoyer_telegram(texte_a_envoyer)
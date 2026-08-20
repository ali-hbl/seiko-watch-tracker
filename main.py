import os
import requests
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# 1. Chargement de la clé API Groq depuis le fichier .env
load_dotenv()

# =======================================================
# COMPOSANT 1 : LE LLM (Le Cerveau - Nouvelle méthode CrewAI)
# =======================================================
llm_groq = LLM(
    model="groq/qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY")
)

# =======================================================
# COMPOSANT 2 : L'OUTIL (Les Mains)
# =======================================================
@tool("Recherche_Web_DuckDuckGo")
def recherche_web(requete: str) -> str:
    """
    Indispensable pour chercher des informations récentes sur internet.
    Prend en entrée une requête de recherche (string) et retourne un résumé 
    des 3 meilleurs résultats sous forme de texte.
    """
    try:
        results = DDGS().text(requete, max_results=2)
        if not results:
            return "Aucun résultat trouvé pour cette recherche. Essaie de reformuler."
        
        formatted_results = []
        for res in results:
            formatted_results.append(
                f"Titre : {res['title']}\nLien : {res['href']}\nExtrait : {res['body']}"
            )
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        return f"Erreur technique : {str(e)}"

# =======================================================
# COMPOSANT 3 : L'AGENT (Le Persona)
# =======================================================
veilleur_tech = Agent(
    role="Expert en Veille Technologique",
    goal="Trouver, analyser et synthétiser les dernières actualités tech pertinentes.",
    backstory="""Tu es un analyste tech senior en Belgique. 
    Tu as l'habitude de parcourir le web pour trouver des informations complexes et de les résumer 
    de manière claire. Tu vérifies toujours tes sources.""",
    verbose=True, 
    allow_delegation=False, 
    max_iter=3, 
    tools=[recherche_web], 
    llm=llm_groq # On passe notre nouveau LLM natif ici
)

# =======================================================
# COMPOSANT 4 : LA TÂCHE (La Mission)
# =======================================================
mission_recherche = Task(
    description="""
    Fais une recherche sur le web pour trouver les 3 informations les plus importantes concernant 
    les nouveautés du framework 'LangChain' annoncées lors du dernier trimestre. 
    """,
    expected_output="""
    Un rapport structuré en Markdown avec un titre, une intro, 3 points clés (avec lien URL) et une conclusion.
    """,
    agent=veilleur_tech
)

# =======================================================
# ORCHESTRATION : LE CREW (L'Équipe)
# =======================================================
equipe = Crew(
    agents=[veilleur_tech],
    tasks=[mission_recherche],
    process=Process.sequential, 
    verbose=True
)

# =======================================================
# FONCTION D'ENVOI TELEGRAM
# =======================================================
# =======================================================
# NOUVEAU COMPOSANT : FONCTION D'ENVOI TELEGRAM (SÉCURISÉE)
# =======================================================
def envoyer_telegram(message):
    """Envoie un message texte via le bot Telegram avec un mécanisme de secours"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Erreur : Les identifiants Telegram manquent dans le fichier .env")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Tentative 1 : Avec le formatage Markdown
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Rapport envoyé avec succès sur Telegram (avec formatage) !")
        
    except requests.exceptions.HTTPError:
        print("⚠️ Telegram a rejeté le formatage Markdown. Nouvel essai en texte brut...")
        
        # Tentative 2 : Si la tentative 1 échoue, on renvoie la même chose mais en texte brut pur
        payload_secours = {
            "chat_id": chat_id,
            "text": message
        }
        
        try:
            response_secours = requests.post(url, json=payload_secours)
            response_secours.raise_for_status()
            print("✅ Rapport envoyé avec succès sur Telegram (en texte brut) !")
        except Exception as e:
            print(f"❌ Échec définitif de l'envoi Telegram : {e}")

# =======================================================
# EXECUTION
# =======================================================
if __name__ == "__main__":
    print("Démarrage de l'agent (Recherche en cours)...")
    
    # 1. On lance l'agent
    resultat_final = equipe.kickoff()
    
    # 2. CrewAI renvoie un objet complexe, on le convertit en texte brut (string)
    rapport_texte = str(resultat_final)
    
    print("\n\n================================================")
    print("MISSION TERMINÉE")
    print("================================================\n")
    
    # 3. On coupe le texte à 4000 caractères max pour éviter le bug Telegram
    texte_a_envoyer = rapport_texte[:4000]
    
    # 4. On déclenche l'envoi vers le téléphone
    envoyer_telegram(texte_a_envoyer)
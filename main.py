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
    model="groq/qwen/qwen3.6-27b", # On reprend notre expert
    api_key=os.getenv("GROQ_API_KEY"),
    max_completion_tokens=800 # La méthode moderne pour limiter la taille de la réponse
)

recherche_google = SerperDevTool()

chasseur_montres = Agent(
    role="Personal Shopper Expert en Horlogerie",
    goal="Trouver 3 offres pour la Seiko SBTR027 et identifier le prix le plus bas.",
    backstory="""Tu es un expert en montres japonaises (JDM). Ton client cherche la Seiko SBTR027.
    RÈGLE N°1 : N'utilise JAMAIS les balises <think>.
    RÈGLE N°2 : Cherche via Google et extrais le prix le plus bas trouvé (converti en EUROS).""",
    verbose=True, 
    allow_delegation=False,
    max_iter=1, # 1 seule recherche max pour ne pas exploser la mémoire
    tools=[recherche_google],
    llm=llm_groq 
)

mission_seiko = Task(
    description="""
    Trouve 3 offres actuelles pour la Seiko SBTR027.
    IMPORTANT - FORMAT DE RÉPONSE OBLIGATOIRE :
    Sur la toute première ligne de ta réponse, tu DOIS écrire : "PRIX_MIN: [prix]" (où [prix] est uniquement le nombre du prix le plus bas en euros, sans le symbole €. Par exemple : PRIX_MIN: 135).
    Ensuite, saute une ligne et rédige ton rapport normal avec les 3 offres.
    """,
    expected_output="Ligne 1: PRIX_MIN: [nombre]. Suivi du rapport en texte brut (SANS utiliser d'astérisques **).",
    agent=chasseur_montres
)

equipe = Crew(
    agents=[chasseur_montres],
    tasks=[mission_seiko],
    process=Process.sequential, 
    verbose=True
)

def envoyer_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(os.getenv("TELEGRAM_CHAT_ID")).strip()
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Envoie en texte simple
    requests.post(url, json={"chat_id": chat_id, "text": message})

if __name__ == "__main__":
    resultat_final = equipe.kickoff()
    rapport_texte = str(resultat_final)
    
    # Nettoyage du "think"
    if "</think>" in rapport_texte:
        rapport_nettoye = rapport_texte.split("</think>")[-1].strip()
    else:
        rapport_nettoye = re.sub(r'<think>.*', '', rapport_texte, flags=re.DOTALL).strip()
    
    # Nettoyage des astérisques pour rendre le texte propre
    rapport_nettoye = rapport_nettoye.replace("**", "").replace("*", "-")
    
    # ==========================================
    # LOGIQUE DE DÉCLENCHEMENT (SEUIL DE 120€)
    # ==========================================
    
    # Cherche le nombre caché après PRIX_MIN:
    match = re.search(r'PRIX_MIN:\s*(\d+)', rapport_nettoye)
    
    if match:
        prix_minimum = int(match.group(1))
        print(f"Prix le plus bas trouvé aujourd'hui : {prix_minimum}€")
        
        if prix_minimum < 120:
            print("Prix sous les 120€ ! Envoi de l'alerte Telegram...")
            titre = "🚨 ALERTE PRIX : SEIKO SBTR027 SOUS LES 120€ ! 🚨\n\n"
            texte_a_envoyer = titre + rapport_nettoye[:3900]
            envoyer_telegram(texte_a_envoyer)
        else:
            print("Le prix est supérieur ou égal à 120€. Pas de message envoyé aujourd'hui.")
            
    else:
        print("L'Agent n'a pas formaté le prix correctement. On envoie quand même par sécurité.")
        titre = "⌚️ RAPPORT SEIKO SBTR027 (Format inattendu) ⌚️\n\n"
        texte_a_envoyer = titre + rapport_nettoye[:3900]
        envoyer_telegram(texte_a_envoyer)
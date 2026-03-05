## Über SAGE

SAGE (oder OPACA LLM UI) ist ein leistungsstarker Chatbot, der Benutzeranfragen erfüllen kann, indem er Aktionen einer verbundenen OPACA‑Plattform aufruft. Er besteht aus zwei Teilen: dem eigentlichen UI/Frontend, implementiert in JavaScript und Vue, und einem Backend, das eine LLM‑API anbietet. SAGE enthält einige eigenen Aktionen, aber erhält die meiste Funktionalität von der verbundenen OPACA‑Plattform.


## Wie benutze ich SAGE?

1. Verbinde dich mit einer OPACA‑Runtime‑Plattform.
2. Sieh dir die bereitgestellten Agenten & Aktionen an oder wirf einen Blick auf die Beispiel‑Abfragen.
3. Wähle die zu verwendende Prompting‑Methode (z.B. Tool‑LLM, Simple, ...) und prüfe deren Konfiguration.
4. Probiere eine der Beispiel‑Abfragen aus oder tippe deine eigene Frage in das Chat‑Fenster.
5. Warte ein paar Sekunden auf die Antwort des LLM, prüfe die Debug‑Ausgabe für "Behind‑the‑Scenes"-Informationen und stelle Nachfragen.


## Wie funktioniert SAGE?

Die Architektur besteht aus einem Frontend (dieses UI) und einem Backend, das eine API bereitstellt, die vom Frontend aufgerufen wird. Das Backend bietet verschiedene Prompting‑Methoden bzw. Interaktionsmodi (siehe weiter unten), von denen jeder eigene Stärken und Schwächen hat. Jeder dieser Modi hat Zugriff auf alle Aktionen, die von den Agenten auf der verbundenen OPACA‑Plattform bereitgestellt werden.

Das Frontend enthält verschiedene Seitenleisten, die ein- oder ausgeklappt werden können und z.B. Informationen zu den verfügbaren Agenten, Beispiel‑Abfragen, Konfigurationen der verschiedenen Prompt‑Methoden und detaillierte Debug‑Ausgaben bereitstellen. Der Nachrichtenverlauf und die Konfiguration werden in der Browsersitzung gespeichert, sodass mehrere Nutzer das System parallel verwenden können.

Für detailliertere Informationen besuche bitte die GitHub‑Seite des Projekts (Link am Ende dieser Seite).


## Was passiert mit meinen Daten?

Dein Chat‑Verlauf wird im Backend im Speicher gehalten und über eine UUID in einem Browser‑Cookie mit dir verknüpft. Andere Nutzer des Systems können deinen Chat‑Verlauf nicht einsehen, es sei denn, sie erhalten dein Sitzungs‑Cookie. Das Cookie hat eine Lebensdauer von 30 Tagen und wird bei jeder Anfrage erneuert. Sobald das Cookie abläuft, werden die Chat‑Verläufe aus dem Backend entfernt. Du kannst jederzeit einzelne Chats löschen, um deinen Chat‑Verlauf zu entfernen. Hinweis: Wenn du das Cookie in deinem Browser löschst, wird ein neues Cookie ausgestellt und du verlierst die Möglichkeit, den alten Verlauf zurückzusetzen (er wird dann gelöscht, wenn das alte Cookie abläuft).

Deine Chat‑Eingaben werden an das konfigurierte LLM (z.B. GPT oder ein lokal installiertes LLM) weitergeleitet und können von den Unternehmen, die diese LLMs betreiben, ausgewertet werden. SAGE selbst (Frontend und Backend) prüft oder bewertet deine Eingaben und Ergebnisse nur insofern, als es nötig ist, um die jeweiligen Werkzeuge aufzurufen und die Antwort zu formatieren. Weder Eingaben noch Ergebnisse werden dauerhaft gespeichert, archiviert oder an Dritte weitergegeben.


## Weitere häufig gestellte Fragen

**Was ist OPACA und warum muss ich mich damit verbinden?**  
OPACA ist ein Framework, das Multi‑Agent‑Systeme mit Container‑Technologien und Microservices kombiniert. OPACA ermöglicht dem Assistenten die Nutzung von Werkzeugen. Ohne Verbindung können tool‑basierte Aktionen nicht ausgeführt werden.

**Was sind Werkzeuge/Dienste und wie erfahre ich, welche verfügbar sind?**  
Jedes dem LLM verfügbare Werkzeug entspricht einer Aktion, die von einem der Agenten auf der OPACA‑Plattform bereitgestellt wird. Sie werden automatisch geladen, wenn du dich mit einem Backend verbindest. Verfügbare Werkzeuge siehst du im Tab "Agents & Actions".

**Was ist der Unterschied zwischen den Interaktionsmodi?**  
- Simple: Ein einfacher Prompt, der die verfügbaren Aktionen aufführt und das LLM in einer Schleife abfragt; die zu ausführenden Aktionen werden aus der LLM‑Ausgabe extrahiert.  
- Simple‑Tools: Ein einzelner Agent wie bei 'Simple', jedoch unter Verwendung des 'tools'-Parameters.
- Tool‑LLM: Drei Agenten nutzen den integrierten 'tools'-Parameter und bieten ein gutes Gleichgewicht zwischen Geschwindigkeit, Einfachheit und Funktionalität.  
- Self‑Orchestration: Ein zweistufiger Ansatz, bei dem ein Orchestrator mehrere Gruppen von Worker‑Agenten delegiert, die jeweils für unterschiedliche OPACA‑Agenten zuständig sind.  

**Welche Prompts kann ich verwenden und wo kann ich mehr erfahren?**  
Verwende natürliche Sprache, um zu beschreiben, was du möchtest. Sieh dir die Prompt‑Bibliothek für Beispiele und Vorlagen an. Das LLM kann dir helfen, die verschiedenen Werkzeuge der Agenten auf der OPACA‑Plattform zu nutzen oder allgemeine Fragen zu beantworten.

**Kann ich eigene Werkzeuge/Dienste einsetzen?**  
Ja. Wenn du die Backend‑URL und Zugangsdaten hast, kannst du neue AgentContainers bei OPACA bereitstellen und deren Aktionen als zusätzliche Werkzeuge verwenden. Schaue dir dazu das verlinkte Python SDK am Ende dieser Seite an, um zu erfahren, wie du deine eigenen AgentContainers entwickeln und bereitstellen kannst.


## Weiterführende Literatur

* <a href="https://github.com/GT-ARC/opaca-llm-ui" target="_blank">SAGE auf GitHub</a>
* <a href="https://github.com/GT-ARC/opaca-core" target="_blank">OPACA auf GitHub</a>
<a href="https://github.com/GT-ARC/opaca-python-sdk" target="_blank">OPACA Python SDK auf GitHub</a>
* <a href="https://go-ki.org/" target="_blank">Go-KI Projekt</a>
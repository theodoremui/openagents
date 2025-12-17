For small talk, chitchat, or simple greetings (please provide a robust generalization for "chitchat" queries from the user), why is the moe orchestrator should simply shunt to and only select the chitchat agent to return a chitchat response as soon as possible.  Right now, as shown in the attached image, the "wiki agent" is selected with additional processing -- which is a mistake.   Investigate deeply on root causes and fix systematically.

Visually, the "minimap" is too large on the right panel.  Shrink that by 40% by size.

For the mouse hover-over dialog boxes in the right panel, they should be vislble at the top without being obscured by the boxes and edges underneath.  Investigate deeply on @frontend_web  and systematically propose fixes for all the issues, then test your fixes carefully.  Finally fix all issues uncovered thoroughly.


> '/Users/pmui/Desktop/Screenshot 2025-12-14 at 12.06.37 AM.png': why is asking 
for direction not select the "map" agent nor the "geo" agent?  It seems 
selecting for "perplexity", "one", and "chitchat" is not the right ones.  
Investigate how the moe orchestrator ended selecting the wrong agents 
generically, and fix the root causes fundamentally.   It may be that the 
semantic embedding search needs some refinement here to work properly for 
routing or map or geo type queries. 
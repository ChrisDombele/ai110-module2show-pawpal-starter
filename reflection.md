# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
  -  The design separates the pets and the owners from the logic that builds the plan as well as the plan that is produced. The owner has multiple pets and 1 group of preferences. Every pet has tasks. The scheduler reads the contraints and makes the daily plan. The plan contains scheduled items. Each one records why its task was placed. The enums keep task categories fixed and the helper calsses such as conflict support conflict detection.
- What classes did you include, and what responsibilities did you assign to each?
    - The UML design includes the classes Owner, Pet, Task, Preferences, TimeWindow, Scheduler, DailyPlan, ScheduledItem, Conflict, and Enums. Owner holds the info for each pet owner. Pet holds the information for each pet. Task represents one activity. Preferences holds the owners preferences. TimeWindow is the start and end time. Scheduler holds the planning logic. Conflict records tasks that clash. DailyPlan holds the scheduled items. ScheduledItem pairs a task with its start and end time. Enums define the allowed values for categories, repeat rules, etc.
**b. Design changes**

- Did your design change during implementation?
  - The desgin did change during implementation. The class remained the same but the behaviors changed.
- If yes, describe at least one change and why you made it.
  - One change that was made was the behavior of ScheduledItem. Before it did not have pet_name as a attribute. This needed to be added so then the UI could show which pet beloned to which task that was scheduled. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

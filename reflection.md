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
  - The constraints that are considered of the following. Time available, priority, owners day window, blocked times, requested times, preferred task types, what is due today, and if there are no overlaps.
- How did you decide which constraints mattered most?
  - The decision to chooose which constraints matterd most where made by choosing hard limits vs preferences. The hard limits are ones that can't be broken but the preferences dont block any tasks. Along with preferences would be the priority and tie breakers.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
  - A tradeoff that is made is that the scheduler goes through tasks in priority order. It places each one of the tasks in the earliest slot available. The scheduler does not go bakc to rearrange the choices from earlier. An example would be if an owner had 60 minutes to work with and there is a 40 minute high priority task, and then a 30 minute less of a priorty task, the 30 minute task would be skipped.
- Why is that tradeoff reasonable for this scenario?
  - For this sceneario, I believe the tradeoff is reasonable. I say this because I think a busy owner would prefer to have a task thats a priority on the schedule and get it done over a lower priority that could be done another time.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
    - I used AI to desgin the UML based on inputs that I had given it. Those inputs were a general guideline on the types of classes that should be in the code and what they would outline. I also had AI refactor code that was less efficient and had less readability. Tests were also created with the help of AI to make sure the functions that were implemented worked as intended.
- What kinds of prompts or questions were most helpful?
  - The prompts and questions that were most helpful were the ones were I could give it key peices of information such a the requirments for how the app should fuction. This would include function names and classes that were given and ones that I came up with on my own.
**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
  - I did not accept the way the AI handled a fuction to get all tasks. I did not accept it because it was different to how the requirements wanted it to be handled.
- How did you evaluate or verify what the AI suggested?
  - I evaluted and verified based on the instructions that are displayed on project 5 steps and requirments.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
  - The behaviors that were tested are data management, task state and recurrence, filtering, ranking, plan generation, conflict detection and explanation, and time windows.
- Why were these tests important?
  - These tests were important because the scheduler makes a lot of decisions and any small bug like a wrong sort order would produces a plan that would be against what was intended by the user. The tests also test for edge cases. Cases in which I may have missed. Tests are also needed so other changes that are made when code is being refactored dont interfere with the logic that is already confrimed working.

**b. Confidence**

- How confident are you that your scheduler works correctly?
  - In terms of confidence, I am 90% sure that the scheduler works correctly. I would say 90% becasue I believe that any piece of softwar should be tested not only by the developer but by other users. This introduces ideas and other edge cases that have not been thought of.
- What edge cases would you test next if you had more time?
  - Some edge cases that I can think of that could be tested if I had more time would be time overflow to the next day for a task, times of tasks that fit exactly into a time frame, duplicate inputs, every task being blocked, large inputs and UI behavior. There are plenty more tests that could be thought of given enough time and users.
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
  - I am most satisfied with the scheduler. The ability to detect time issues, accurately come up with a schedule based on preferences, and have a clean simple UI along with it is a good outcome.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
  - For another iteration, based on user use, bugs, and feedback, I would add other functionality or take some away. I would also update the UI to be more clean and simple.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
  - From this project, I learned that coming up with a clear plan with diagrams and examples helps improve the output of the product rather than prompting a vague sense of a product and working from there with more prompts. The process to creating a viable product would be faster and smoother.

## Inspiration

Have you ever seen a cool project someone's made, and you really want to know how it works and how it was built, but you can't get over the hump of going through a billion files and folders? Learning from others is one of the best ways to improve and learn new things, but we believe that this sort of learning is growing more and more inaccessible; with so many new technologies and tools coming out all the time, and projects often being unreadable, we believe that there is a disproportionate lack of educational tools compared to how well new technologies such as AI agents are suited to the task.

## What it does

Our project takes in any public Github repository and separates the history into "milestones", creating a readable project timeline that allows you to put yourself in the developer's shoes and understand the iterative design process. Using AI agents, we intelligently process only the necessary context from git commits and objects in order to lazily retrieve expensive file diffs. The whole stack is heavily optimized for performance in order to create a seamless user experience.

## How we built it

We interface with Git using python's subprocess module. We use FastAPI to serve our backend and our frontend is a simple react/nextJS layer. For our AI agent, we use openai-agent with models powered by Cerebras for blazing-fast performance. Cerebras was especially important; it was significantly faster than every other model, which let us provide a seamless timeline streaming interface. To provide a comprehensive full-project summary, we used Cohere.

In our gallery, you can see RepoStory telling you exactly how we built it!

## Challenges we ran into

The project can be thought of as having 4 main steps:

- Fetching: this is where Github objects are programmatically queried and loaded in memory/storage.
- Milestone detection: this is a challenging tasks that asks us what the best way to define a "Milestone" is; Milestones are defined by start and end commits, and have to encode data that will allow an AI agent to process the milestone, creating a key data availability problem.
- Processing: in this step, we take raw milestones and use the power of NLP and AI agents to create data for our front facing application. The AI agent is trained to lazily collect data about the commits in the milestone in steps of increasing complexity, then finally use that data to choose files to examine (e.g. it's more likely to query the diff for mymodule.py, than node_modules, for example).
- Frontend: Create a smooth UX for the user of the application. Super simple: just paste in a project, and watch the timeline as it smoothly generates. Required streaming data about the agent's tool uses to keep the user in the loop.

Let's talk about the main problems:

### Performance

Performance is our #1 priority, from the top to bottom of our entire stack. When we initialize a git repository, we don't fetch any blobs; we only fetch git tree objects. Many git operations rely on finding diffs between blobs; when we do these, we have to make sure those operations are executed as little as possible.

Here's one large architecture problem that we're really proud of:
For our system, we want to select commit hashes that represent the edges of "milestones". The naive strategy is to select based on groups of N commits. However, this is not a good idea as the contents of commits are very varied and there are other factors such as merge commits. People also tend to commit at different frequencies.

For our initial naive approach, we simply selected every single merge commit, as these merges indicate the end of some unit of work done. However, this is also very inconsistent; people who use a rebase strategy do not produce merge commits, and this would simply not work at all on completely linear histories.

For our final approach, we devised a super cool solution. We created heuristics that could roughly measure "work done" between two commits, and output it as a scalar; then starting from the first commit, we want to find the next commit that exceeds the threshold value. Assuming that our measurement of "work done" is increasing, we can binary search for this commit!

Git provides a "bisect" utility that is usually used for finding the last "good" commit before some bug was introduced. You mark a bad commit and a good commit, and the bisect tool will iterate through some commits, asking you to mark them as bad/good, effectively binary searching for the last bad commit. You can provide this tool with a script that can check whether the commit is bad or good automatically. Thus, we can use this to perform our procedure.

[Git bisect docs](https://git-scm.com/docs/git-bisect)

When starting from commit A, we can mark A as a "bad" commit, and the latest commit as a "good" commit. We also have this script:

```bash
../../scoregen.py <ref1> <ref2> --limit <float>
```

scoregen.py will exit with code 1 if the "work" between the two references is greater than the limit. Thus, we can pass it in to git bisect, and it will eventually land on our desired commit!

Our project was full of super interesting problems with really interesting solutions.

## Accomplishments that we're proud of

- Working git subprocess interface; the amount of work we put into ensuring we had a nice, modular git interaction system, as well as hyper-optimizing the performance
- Working agentic AI subsystem able to dynamically load file diffs to acquire its own context
- Working milestone selection framework and strategy

## What we learned

- Git internals! Git is such a complex and amazing piece of software under the hood, but most people only interact with it on a surface level, so it's really cool to learn more about how it works.
- Sleep is overrated

## What's next for RepoStory

We wanted to implement a diff viewer for the files, along with the option to explain specific lines. These would make great additions to our UX.

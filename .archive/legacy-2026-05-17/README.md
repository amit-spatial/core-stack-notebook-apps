# Corestack Applets

Implementation of Marimo Notebooks, webapps,  molab, https://github.com/marimo-team, so that I can build detailed interactive applets showcasing the usage of Core Stack and to let people use these deployed applications as end to end core-stack usecases, with all different kinds of visualisations, analysis, interactive inputs, highlights, easy multi format exports, and showcasing whole potential of CoreStack and Importance of doing this analysis with Core stack approach os using micro watershed as the primary level of geospatial analysis with data obtained from different satellite imageries, and shape files, and some vectorised (earlier, raster) output obtained from use of corestack API (stored in .env file) or provided interactively with input (hidden) in notebook. 


Currently, I am just collating some of previously creating notebooks, which may not work now, as there have been a lot of recent updates in https://github.com/core-stack-org/, specifically https://github.com/core-stack-org/core-stack-backend. We can check all the data current repo exposes through Public APIs. (the updated repo is available for reading at `/mnt/y/core-stack-org/core-stack-backend/`; A fairly updated Documentation of the repo can be found at: `https://deepwiki.com/core-stack-org/core-stack-backend` (Last indexed: 16 May 2026 (c8dc17))  We need to use fetch the data from apis, such as https://api-doc.core-stack.org/api/v1/get_active_locations/, and build pathways for people to get data for some geography at the scale they like, and interactively do the analysis they want to do, along with interactive visualisations, outputs, and other products. Core Stack Data properties and its metadata can also be obtained from core stack STAC specs. People should get the full picture of what is available and what they can try out. And we should also build some in-depth geospatial analysis to show true power of the Core-Stack approach as well. 

I have also added some marimo skill files, some example notebooks. 

Also refer to: 
1. https://deepwiki.com/marimo-team/marimo,
2. https://docs.marimo.io/guides/generate_with_ai/skills/
3. https://github.com/marimo-team/awesome-marimo#libraries
4. https://github.com/marimo-team/marimo/tree/main/examples
5. https://evoc.readthedocs.io/en/latest/


These would later be deployed to our main website core-stack.org/webapps/, and our MKDocs based https://docs.core-stack.org/ via https://github.com/core-stack-org/core-stack-docs. 


Always use uv. I have globally intalled marimo as a uv tool as well: `uv tool install marimo`, along with locally `uv add "marimo[recommended]"`.
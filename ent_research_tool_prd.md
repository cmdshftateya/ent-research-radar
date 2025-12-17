# ENT Research Tool
AI note: do not implement things marker later
AI note: if you are going to do something expensive, ask me before proceeding

I need a tool to help me cold email professors in a calibrated way. I need to know about their research interests, their collaborators, how "cracked" they are at research (h-index or a similar measurement is a good proxy for that). I need to know if they have their own lab. I really only care about researchers who work at four universities:

1. [Northwestern University](https://www.oto-hns.northwestern.edu/faculty/a-z.html)
2. [University of Chicago](https://www.uchicagomedicine.org/conditions-services/ear-nose-throat/physicians)
3. [University of Illinois Chicago](https://chicago.medicine.uic.edu/otolaryngology/people/faculty/)
4. [Rush Medical School](https://www.rush.edu/locations/rush-otolaryngology-head-and-neck-surgery-chicago)

( later: implement online research opportunities at UMN or UMich)

## User stories
1. As a medical student, I want a list of a professors that I can scroll through, with the following information for each of them:
    1. Their name
    2. Their email
    3. Their institution (later: implement their resume by scraping Linkedin)
    4. Their top 10 most common research tags related to ENT
2. Once I click on a certain professor, I can see the most recent 20 publications they made, including the titles, co-authors (highlight their names), and dates of the publication. I should be able to click on a link
3. On the page, I should be able to open up a sidebar on the left that has a textbox where I can write a draft email, along with a copy/paste button so I can copy my text into my email
4. I should be able to a run a command line script to get this all up and running to check on my data, but it should run every Monday and notify me locally on my laptop. IDK how to implement this, but I need your help

## Proposed workflow
- make a plan to implement this by first getting a list of all the professors at the four institutions and storing that list in a database (idk how to implement this simply)
- for each professor, write a script that can get the details about them
- Once you have the per-professor details, make the summary page. 

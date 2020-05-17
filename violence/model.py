"""
A simple victim x aggressor encounter model
================================
Directly adapted from mesa example which is inspired by the model found in NetLogo:
    Wilensky, U. (1997). NetLogo Wolf Sheep Predation model.
    http://ccl.northwestern.edu/netlogo/models/GunsPredation.
    Center for Connected Learning and Computer-Based Modeling,
    Northwestern University, Evanston, IL.
"""
import os
if __name__ == '__main__':
    os.chdir('/home/furtadobb/MyModels/home_violence/')

import numpy as np
import pandas as pd
from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector


from violence.agents import Person, Family
from violence.schedule import RandomActivationByBreed
from violence.input import generator
from violence.input.generator import metropolis


class Home(Model):
    """
    A Home Violence Simulation Model
    """

    verbose = True  # Print-monitoring
    description = 'A model for simulating the victim aggressor interaction mediated by presence of violence.'

    def __init__(self, height=40, width=40,
                 initial_families=400,
                 metro='BRASILIA',
                 gender_stress=.8,
                 under_influence=.1,
                 has_gun=.5,
                 is_working_pct=.8,
                 chance_changing_working_status=.05,
                 pct_change_wage=.05,
                 model_scale=1000):
        """
        A violence violence model of Brazilian metropolis

        """
        super().__init__()
        # Set parameters
        self.height = height
        self.width = width

        self.initial_families = initial_families
        self.metro = metro

        self.gender_stress = gender_stress
        self.under_influence = under_influence
        self.has_gun = has_gun
        self.is_working_pct = is_working_pct
        self.chance_changing_working_status = chance_changing_working_status
        self.pct_change_wage = pct_change_wage
        self.model_scale = model_scale

        self.schedule = RandomActivationByBreed(self)
        self.grid = MultiGrid(self.height, self.width, torus=True)
        # Model reporters. How they work: lambda function passes model and other parameters.
        # Then another function may iterate over each 'agent in model.schedule.agents'
        # Then server is going to collect info using the keys in model_reporters dictionary
        model_reporters = {
            "Person": lambda m: self.count_type_citizens(m, "person"),
            "Victim": lambda m: self.count_type_citizens(m, "victim"),
            "Aggressor": lambda m: self.count_type_citizens(m, "aggressor"),
            "Stress": lambda m: self.count_stress(m)}
        self.datacollector = DataCollector(model_reporters=model_reporters)

        # Create people ---------------------------------------------------
        # Parameters to choose metropolitan region
        # More details available at input/population
        params = dict()
        params['PROCESSING_ACPS'] = [self.metro]
        params['MEMBERS_PER_FAMILY'] = 2.5
        params['INITIAL_FAMILIES'] = self.initial_families
        people, families = generator.main(params=params)
        # General random data for each individual
        n = sum([len(f) for f in families])
        working = np.random.choice([True, False], n, p=[self.is_working_pct, 1 - self.is_working_pct])
        influence = np.random.choice([True, False], n, p=[self.under_influence, 1 - self.under_influence])
        gun = np.random.choice([True, False], n, p=[self.has_gun, 1 - self.has_gun])
        w = np.random.beta(2, 5, n)
        i = 0
        for fam in families:
            # 1. Create a family.
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            # Create a family
            family = Family(self.next_id(), self, (x, y))
            # Add family to grid
            self.grid.place_agent(family, (x, y))
            self.schedule.add(family)
            # Marriage procedures
            engaged = ['male_adult', 'female_adult']
            to_marry = list()
            # Add people to families
            for each in fam:
                person = people.loc[each]
                doe = Person(self.next_id(), self, (x, y),
                             # From IBGE's sampling
                             gender=person.gender,
                             age=person.age,
                             color=person.cor,
                             address=person.AREAP,
                             years_study=person.years_study,
                             # End of sampling
                             is_working=working[i],
                             reserve_wage=w[i],
                             under_influence=influence[i],
                             has_gun=gun[i])
                # Marrying
                if len(engaged) > 0:
                    if person.category in engaged:
                        engaged.remove(person.category)
                        to_marry.append(doe)
                # Change position in the random list previously sampled
                i += 1
                self.grid.place_agent(doe, (x, y))
                self.schedule.add(doe)
                family.add_agent(doe)
            # 2. Marry the couple
            if len(to_marry) == 2:
                to_marry[0].assign_spouse(to_marry[1])

            # 3. Update number of family members
            for member in family.members.values():
                member.num_members_family = len(family.members)

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()
        # collect data
        self.datacollector.collect(self)

        # Check if step will happen at individual levels or at family levels or BOTH
        if self.verbose:
            print([self.schedule.time, self.schedule.get_breed_count(Person)])

        # New condition to stop the model
        if self.schedule.get_breed_count(Person) == 0:
            self.running = False

    @staticmethod
    def count_type_citizens(model, condition):
        """
        Helper method to count agents by Type.
        """
        count = 0
        for agent in model.schedule.agents:
            if isinstance(agent, Person):
                if agent.category == condition:
                    count += 1
        return count

    @staticmethod
    def count_stress(model):
        count, size = 0, 0
        for agent in model.schedule.agents:
            if isinstance(agent, Family):
                count += agent.context_stress
                size += 1
        return count / size

    def run_model(self, step_count=200):

        if self.verbose:
            print('Initial number of people: ', self.schedule.get_breed_count(Person))

        # Steps are not being set here, but on superclass. Changes should be made in the step function above!
        for i in range(step_count):
            self.step()

        if self.verbose:
            print('')
            print('Final number People: ', self.schedule.get_breed_count(Person))


def generate_output():
    # Running for all metropolis
    output = pd.DataFrame(columns=['metropolis', 'stress'])
    for metro in metropolis:
        home = Home(metro=metro)
        for i in range(10):
            home.step()
        model_df = home.datacollector.get_model_vars_dataframe()
        output.loc[output.shape[0]] = [metro, model_df.loc[9, 'Stress']]
    output.to_csv('output.csv', sep=';', index=False)


if __name__ == '__main__':
    # Bernardo's debugging
    # generate_output()

    # To generate a number of runs of a metro, before BatchRunner
    # otp = pd.DataFrame(columns=['metropolis', 'stress'])
    # metro = 'JOINVILLE'
    # for i in range(20):
    #     home = Home(metro=metro)
    #     for j in range(10):
    #         home.step()
    #     model_df = home.datacollector.get_model_vars_dataframe()
    #     otp.loc[otp.shape[0]] = [metro, model_df.loc[9, 'Stress']]
    # otp.to_csv('joinville.csv', sep=';', index=False)
    pass
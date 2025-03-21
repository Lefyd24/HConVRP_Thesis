from solver_modules.models import Customer, VehicleType, Vehicle
from solver_modules.helpers import create_node_matrix, colorize
import yaml
import os
from flask import current_app
import networkx as nx
import pandas as pd
import numpy as np

class SolutionLoader:
    def __init__(self):
        self.register_constructors()
        
    # Define custom constructors
    def customer_constructor(self, loader, node):
        data = loader.construct_mapping(node, deep=True)
        return Customer(
            id=data['id'],
            coordinates=tuple(data['coordinates']),
            demands=data['demands'],
            planning_horizon=data['planning_horizon'],
            service_time=data['service_time']
        )

    def vehicle_type_constructor(self, loader, node):
        data = loader.construct_mapping(node, deep=True)
        return VehicleType(
            vehicle_type_name=data['vehicle_type_name'],
            available_vehicles=data['available_vehicles'],
            capacity=data['capacity'],
            fixed_cost=data['fixed_cost'],
            variable_cost=data['variable_cost'],
            speed=data['speed']
        )

    def vehicle_constructor(self, loader, node):
        data = loader.construct_mapping(node, deep=True)
        return Vehicle(
            id=data['id'],
            vehicle_type=None  # This will be assigned separately
        )
    
    # Register the constructors for the specific tags
    def register_constructors(self):
        yaml.add_constructor('tag:yaml.org,2002:python/object:solver_modules.models.Customer', self.customer_constructor, Loader=yaml.FullLoader)
        yaml.add_constructor('tag:yaml.org,2002:python/object:solver_modules.models.VehicleType', self.vehicle_type_constructor, Loader=yaml.FullLoader)
        yaml.add_constructor('tag:yaml.org,2002:python/object:solver_modules.models.Vehicle', self.vehicle_constructor, Loader=yaml.FullLoader)

    
    def load_solution(self, filename):
        filename = os.path.join(current_app.config['SOLUTION_PATH'], filename)
        with open(filename, 'r') as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
        
        # Load metadata
        metadata = data.get('metadata', {})
        
        # Load solution details
        solution_data = data.get('solution', {})
        planning_horizon = solution_data.get('planning_horizon', 0)
        max_route_duration = solution_data.get('max_route_duration', 0)
        
        # Load depot information
        depot_data = solution_data.get('depot')
        depot = Customer(
            id=depot_data.id,
            coordinates=tuple(depot_data.coordinates),
            demands=depot_data.demands,
            planning_horizon=planning_horizon,
            service_time=0
        )
        
        # Load customers
        customer_data = solution_data.get('nodes', [])
        customers = []
        for c_data in customer_data:
            customer = Customer(
                id=c_data.id,
                coordinates=tuple(c_data.coordinates),
                demands=c_data.demands,
                planning_horizon=planning_horizon,
                service_time=c_data.service_time
            )
            customers.append(customer)
        # Map customer IDs to customer objects for easy lookup
        customer_dict = {customer.id: customer for customer in customers}
        # Add depot to the customer dictionary
        customer_dict[depot.id] = depot

        # Load vehicle types
        vehicle_types_data = solution_data.get('vehicle_types', [])
        vehicle_types = []
        for vt_data in vehicle_types_data:
            vehicle_type = VehicleType(
                vehicle_type_name=vt_data.vehicle_type_name,
                available_vehicles=vt_data.available_vehicles,
                capacity=vt_data.capacity,
                fixed_cost=vt_data.fixed_cost,
                variable_cost=vt_data.variable_cost,
                speed=vt_data.speed
            )
            vehicle_types.append(vehicle_type)
        
        # Generate the distance matrix
        distance_matrix = create_node_matrix(customers, depot)

        # Load vehicles
        vehicles_data = solution_data.get('vehicles', [])
        vehicles = []
        for v_data in vehicles_data:
            vehicle_id = v_data['id']
            vehicle_type = v_data['type']  # 'type' is already a VehicleType object
            vehicle = Vehicle(
                id=vehicle_id,
                vehicle_type=vehicle_type,
                current_location=depot,  # Assuming vehicles start at the depot
                planning_horizon=planning_horizon,
                max_route_duration=max_route_duration,
                distance_matrix=distance_matrix
            )
            vehicles.append(vehicle)
        
        # Load routes
        routes_data = solution_data.get('routes', {})
        routes = {}
        for period, period_routes in routes_data.items():
            routes[period] = []
            for route_data in period_routes:
                vehicle_id = route_data['vehicle_id']
                vehicle = next((v for v in vehicles if v.id == vehicle_id), None)
                if vehicle is None:
                    continue
                route = [customer_dict[cust_id] for cust_id in route_data['route']]
                routes[period].append((vehicle, route))
        
        
        # Load total costs
        total_cost = solution_data.get('total_cost', {})
        
        return {
            'metadata': metadata,
            'planning_horizon': planning_horizon,
            'max_route_duration': max_route_duration,
            'depot': depot,
            'vehicle_types': vehicle_types,
            'vehicles': vehicles,
            'routes': routes,
            'customers': customers,
            'total_cost': total_cost
        }
        
    def create_graph(self, solution):
        """
        Create a graph representation of the solution.
        """

        
        G = nx.DiGraph()
        
        # Add nodes
        for customer in solution['customers']:
            G.add_node(customer.id, demand=customer.demands)
        G.add_node(solution['depot'].id, demand=solution['depot'].demands)
        
        # Add edges
        for period, routes in solution['routes'].items():
            for vehicle, route in routes:
                for i in range(1, len(route)):
                    G.add_edge(route[i-1].id, route[i].id, vehicle=vehicle.id, period=period)
                    
        edges = list(G.edges(data=True))
        
        return G, edges

class SolutionChecker:
    def __init__(self, solution):
        self.planning_horizon = solution['planning_horizon']
        self.max_route_duration = solution['max_route_duration']
        self.depot = solution['depot']
        self.vehicle_types = solution['vehicle_types']
        self.vehicles = solution['vehicles']
        self.routes = solution['routes']
        self.customers = solution['customers']
        self.total_cost = solution['total_cost']
        self.distance_matrix = create_node_matrix(self.customers, self.depot)
        
    def __str__(self) -> str:
        return colorize(f"Solution Checker for {len(self.vehicles)} vehicles and {len(self.customers)} customers initiated.", "GREEN")
    
    def _find_frequent_customers(self) -> list: 
        """
        A frequent customer is considered to be one that has a demand > 0 on more than one period of the planning horizon.
        """
        frequent_customers = []
        for customer in self.customers:
            number_demands = 0
            for period in range(self.planning_horizon):
                if customer.demands[period] > 0:
                    number_demands += 1
                if number_demands > 1:
                    frequent_customers.append(customer)
                    break
        return frequent_customers
    
    def check_vehicle_capacity(self):
        for period, routes in self.routes.items():
            for vehicle, route in routes:
                load = 0
                for customer in route:
                    load += customer.demands[period]
                if load > vehicle.vehicle_type.capacity:
                    print(colorize(f"Vehicle {vehicle.id} exceeded capacity in period {period}. Load: {load}, Capacity: {vehicle.vehicle_type.capacity}.", "RED"))
                    return False
        return True
    
    def check_vehicle_duration(self):
        for period, routes in self.routes.items():
            for vehicle, route in routes:
                duration = 0
                for i in range(1, len(route)):
                    duration += (self.distance_matrix[route[i-1].id, route[i].id] + route[i].service_time)/vehicle.vehicle_type.speed
                if duration > self.max_route_duration:
                    print(colorize(f"Vehicle {vehicle.id} exceeded duration in period {period}. Duration: {duration}, Max Duration: {self.max_route_duration}.", "RED"))
                    return False
        return True
    
    def check_customer_uniqueness(self):
        """
        This constraint ensures that each customer is visited exactly once per period, across all vehicles.
        """
        for period, routes in self.routes.items():
            visited_customers = []
            for vehicle, route in routes:
                for customer in route:
                    if customer in visited_customers and customer.id != self.depot.id:
                        print(colorize(f"Customer {customer.id} visited more than once in period {period}.", "RED"))
                        return False
                    visited_customers.append(customer)
        return True
    
    def check_start_and_return_to_depot(self):
        """
        This constraint ensures that each vehicle starts and ends at the depot.
        """
        for period, routes in self.routes.items():
            for vehicle, route in routes:
                if route[0].id != self.depot.id or route[-1].id != self.depot.id:
                    print(colorize(f"Vehicle {vehicle.id} did not start or end at the depot in period {period}.", "RED"))
                    return False
        return True
    
    def check_customer_service(self):
        """
        This constraint ensures:
        1. Each customer is visited in each period they require service. 
        2. Customers are not visited in periods they do not require service.
        3. All customers are visited at least once.
        """
        visited_customers = set()
        for period, routes in self.routes.items():
            for customer in self.customers:
                visited = False
                for vehicle, route in routes:
                    if customer in route:
                        visited = True
                        visited_customers.add(customer)
                        break
                if not visited and customer.demands[period] > 0:
                    print(colorize(f"Customer {customer.id} not visited in period {period}.", "RED"))
                    return False
                elif visited and customer.demands[period] == 0:
                    print(colorize(f"Customer {customer.id} visited in period {period} without demand.", "RED"))
                    print(f"Customer {customer.id} demands: {customer.demands}")
                    return False
        if len(visited_customers) != len(self.customers):
            print(colorize(f"Total customers visited: {len(visited_customers)} out of {len(self.customers)}.", "RED"))
            return False
        return True
    
    def check_frequent_customers_consistency(self):
        """
        This route ensures that frequent customers are visited in every period they require service, by the same vehicle.
        """
        frequent_customers = self._find_frequent_customers()
        for customer in frequent_customers:
            customer_assigned_vehicles = set()
            for period in range(self.planning_horizon):
                visited = False
                for vehicle, route in self.routes[period]:
                    if customer in route:
                        visited = True
                        customer_assigned_vehicles.add(vehicle)
                        break
                if not visited and customer.demands[period] > 0:
                    print(colorize(f"Frequent customer {customer.id} not visited in period {period}.", "RED"))
                    return False
                elif len(customer_assigned_vehicles) > 1:
                    print(colorize(f"Frequent customer {customer.id} visited by more than one vehicle.", "RED"))
                    return False
        return True
    
    def calculate_solution_cost(self):
        """
        Calculate the total cost of the solution.
        """
        total_cost = 0
        for period, routes in self.routes.items():
            period_cost = 0
            for vehicle, route in routes:
                period_cost += vehicle.fixed_cost
                for i in range(1, len(route)):
                    period_cost += vehicle.variable_cost*((self.distance_matrix[route[i-1].id, route[i].id] + route[i].service_time)/vehicle.vehicle_type.speed)
            total_cost += period_cost
            print(colorize(f"Period {period} cost: {period_cost}", "YELLOW"))
        return total_cost

class SolutionsComparator:
    def __init__(self, solutions:dict):
        self.solutions = solutions
    
    def compare(self):
        """
        Compare the solutions.
        """
        cost_comparison = self._compare_costs()
        time_comparison = self._compare_times()
        #routes_comparison = self._compare_vehicles_per_period()
        
        return {"cost_comparison": cost_comparison, "time_comparison": time_comparison}
    
    def _compare_times(self):
        """
        Compare the times taken to solve the problems.
        """
        times = {}
        for solution_name, data in self.solutions.items():
            times[solution_name] = data['metadata'].get('computation_time_seconds', None)
        
        df = pd.DataFrame(times, index=['Time (s)']).T
        df['Rank'] = df['Time (s)'].rank()
        df.sort_index(inplace=True)
        return df.to_json(orient='index', indent=4)
    
    def _compare_costs(self):
        """
        Compare the costs of the solutions.
        """
        costs = {}
        for solution_name, data in self.solutions.items():
            costs[solution_name] = data['solution']['total_cost'] 
        
        df = pd.DataFrame(costs).T
        df['Total Cost'] = df.sum(axis=1)
        df.drop(df.columns[:df.shape[1]-1], axis=1, inplace=True)
        df['Rank'] = df['Total Cost'].rank().astype(int)
        df.sort_index(inplace=True)
        return df.to_json(orient='index', indent=4)
    
    def _compare_vehicles_per_period(self):
        """
        Compare the number of vehicles used per period.
        """
        vehicles = {}
        routes = {}
        for solution_name, data in self.solutions.items():
            vehicles[solution_name] = [vehicle.get('id') for vehicle in data['solution']['vehicles']]
            routes[solution_name] = data['solution']['routes']
        
        data = []
        all_vehicle_ids = set()

        # Collect all unique vehicle IDs across solutions
        for solution_name, periods in routes.items():
            for period, vehicles in periods.items():
                for vehicle in vehicles:
                    all_vehicle_ids.add(vehicle['vehicle_id'])
                    route_length = len(vehicle['route'])
                    data.append([solution_name, vehicle['vehicle_id'], period, route_length])

        # Create a DataFrame
        df = pd.DataFrame(data, columns=['Solution', 'Vehicle', 'Period', 'Route_Length'])

        # Pivot the table with Solution and Period as the column levels, and Vehicle as the row index
        pivot_table = pd.pivot_table(
            df, 
            values='Route_Length', 
            index='Vehicle', 
            columns=['Period','Solution' ], 
            aggfunc='sum',
            fill_value=0  # Fill missing values with 0
        )

        # Sort columns to ensure proper comparison order
        pivot_table = pivot_table.sort_index(axis=1)
        return pivot_table.to_json(orient='index', indent=4)
            
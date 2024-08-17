This project is an effort to further improve the implementation of the solution proposed in the paper of F. Stavropoulou:
### [The Consistent Vehicle Routing Problem with heterogeneous fleet](https://doi.org/10.1016/j.cor.2021.105644)
> (Computers & Operations Research, Volume 140, 2022, 105644, ISSN 0305-0548)

Paper Abstract:

Customer relationship management is of high importance as it strengthens customer satisfaction. Providing consistent customer service cultivates customer retention and brand loyalty. This paper examines a new customer-oriented routing problem, the Consistent Vehicle Routing Problem with heterogeneous fleet. The objective is to create cost-efficient routing plans, utilising a fixed fleet of vehicles with heterogeneous operational characteristics, variable and fixed costs, while providing consistent customer service over multiple periods. Service consistency consists in person and visiting time consistency. A mathematical model capturing all the attributes of the problem is developed and utilised to solve small-scale instances to optimality. To address larger instances, a hierarchical Tabu Search framework is proposed. The proposed metaheuristic utilises an upper-level Tabu Search and an underlying Variable Neighbourhood Descent algorithm. Computational experiments conducted on existing and new benchmark instances show the flexibility, effectiveness and efficiency of the proposed framework. Various managerial insights are derived by examining the cost of imposing customer service consistency as well as customer–vehicle incompatibility constraints. (https://doi.org/10.1016/j.cor.2021.105644)

# Dataset Information
You may find detailed dataset information inside the directory [HConVRPDatasets_YML](HConVRPDatasets_YML/).

## Basic Concepts & Equations
> **Fleet** 
* A <u>fixed</u> fleet with **heterogeneous depot-returning** vehicles is avalable.
* The fleet consists of **H** vehicle types, each with a different number of available vehicles.
* Each vehicle type **k** has:
    * A carrying capacity **$Q_k$**
    * A maximum operation duration of **T** time units
    * A fixed cost **$F_k$** per vehicle (rental, insurance or capital amortisation cost)
    * A variable cost **$V_k$** per unit distance (fuel, driver and maintenance cost)
    * An average speed of **$B_k$** units
* As each vehicle type **k** has a different average speed, the <u>travel time</u> between two nodes **i** and **j** is calculated as **$t^k_{ij} = \frac{d_{ij}}{B_k}$**, where **$d_{ij}$** is the distance between nodes **i** and **j** and **$B_k$** is the average speed of vehicle type **k**.
* For each edge **(i, j)** there is a corresponding **traversal cost** **$c^k_{ij} = d_{ij} * V_k$**.

> **Compatibility**
* There might be compatability restrictions between vehicles and edges, denoted by **$u^k_{ij}$**.
    * If **$u^k_{ij} = 1$**, vehicle type **k** can traverse edge **(i, j)**.
    * If **$u^k_{ij} = 0$**, vehicle type **k** cannot traverse edge **(i, j)**.

> **Customers**
* The set of customers is denoted by **$N_c$**.
* Each customer $i \in N_c$ poses specific servise requirements $w_{ip}$ and service times $s_{ip}$ for each period $p$.
    * If $w_{ip} = 1$, customer $i$ needs to be serviced in period $p$.
    * If $w_{ip} = 0$, customer $i$ does not need to be serviced in period $p$.
* Each customer must be visited exactly once in the required period.
* For each customer there is a known **service time** $s_{ip}$ and a positive demand $q_{ip}$.
* > Frequent Customers
    * **Driver Consistency**: Imposes that each frequent customer needs to be visited by the same vehicle $m \in M$ in all periods.
    * **Arrival Time Consistency**: Imposes that the difference between the earliest and latest arrival times at a frequent customer does not exceed a specified limit $L$.

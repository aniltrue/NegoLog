# NegoLog

## NegoLog: An Integrated Python-based Automated Negotiation Framework with Enhanced Assessment Components

### IJCAI 2024

## Table of Contents
- [Overview](#overview)
  - [Abstract](#abstract)
  - [Features](#features)
- [Install](#install)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Web-Based User Interface](#web-based-user-interface)
- [Development](#development)
  - [Agent Strategy](#agent-strategy)
  - [Opponent Model](#opponent-model)
  - [Custom Logger](#custom-logger)
- [Citation](#citation)
- [License](#license)

## Overview
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31011/)
[![Version 1.0](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/aniltrue/NegoLog)
[![status developing](https://img.shields.io/badge/status-developing-g.svg)](https://github.com/aniltrue/NegoLog)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/a0fa8198e61b4ac98d8c3b473dcf3658)](https://app.codacy.com/gh/aniltrue/NegoLog/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

### Abstract
The complexity of automated negotiation research calls for dedicated, user-friendly research frameworks that facilitate advanced analytics, comprehensive loggers, visualization tools, and auto-generated domains and preference profiles. This paper introduces NegoLog, a platform that provides advanced and customizable analysis modules to agent developers for exhaustive performance evaluation. NegoLog introduces an automated scenario and tournament generation tool in its Web-based user interface so that the agent developers can adjust the competitiveness and complexity of the negotiations. One of the key novelties of the NegoLog is an individual assessment of preference estimation models independent of the strategies. 

### Features
NegoLog is an automated bilateral negotiation framework to develop and analyze sophisticated intelligent agents. NegoLog provides:

- Easy-to-use negotiation library called **nenv** (**N**egotiation **ENV**ironment)
- **AbstractOpponentModel** class within NegoLog serves as a pivotal component that separates opponent model development from the negotiation process. This innovative architecture allows NegoLog to provide received bids to estimators from the perspective of agents during negotiation. This design choice allows individual evaluation of preference estimation performance of the opponent models without directly utilizing in an agent strategy.
- NegoLog introduces noval **Analytics and Visualization Module** called **logger**. NegoLog offers a range of built-in loggers designed to provide detailed negotiation logs, advanced analysis for evaluating agent strategy and opponent models, and statistical graphs. The evaluations are performed from three aspects: *negotiation process*, *negotiation outcome*, and *preference estimation*.
- **AbstractLogger** class, employing callback mechanisms, empowers researchers and developers to easily implement their own *loggers* within NegoLog. This functionality enables customized analyses, logs, and graphs to be effortlessly integrated into the framework, providing users with enhanced flexibility for their specific research or development needs.
- **Domain Generator Tool** facilitates the creation of diverse negotiation scenarios based on user-defined parameters. This innovative tool automatically generates multiple negotiation domains, empowering users to manipulate the utility distribution and tailor scenarios to their specific needs.
- **Web-based User Interface** to generate diverse scenarios, manipulate tournament configurations, run & monitor tournaments in a user-friendly fashion.

## Install
> **_NOTE:_** This project Python project is tested in [Python 3.10](https://www.python.org/downloads/release/python-31011/), Windows 10 and Ubuntu 18.04.
> Creating a [virtual environment](https://docs.python.org/3.10/library/venv.html) is recommended.

You can install this Python project from the scratch, by following steps:

1. Download whole project from [GitHub](https://github.com/aniltrue/NegoLog).
2. Install [Python 3](https://www.python.org/downloads/release/python-31011/)
3. Download & install required Python libraries via `pip`, as shown below:
    ```bash
    pip install -r requirements.txt 
    ```
4. You can run a tournament as described in [Usage](#usage)

## Usage
NegoLog is accessible through the console (i.e., command line) and a user-friendly Web-based interface.

### Command Line
You can start a negotiation tournament with `run.py` Python script by providing a tournament configuration. Tournament configuration is saved in a [YAML](https://yaml.org/) file. An example command line to run on console:
```bash
python run.py tournament_example.yaml
```

> **_NOTE:_** You can create or edit your own [YAML](https://yaml.org/) file to customize a tournament.

### Web-Based User Interface
[![backend Flask](https://img.shields.io/badge/backend-Flask-blue.svg)](https://flask.palletsprojects.com/en/3.0.x/)
[![frontend React](https://img.shields.io/badge/frontend-React-blue.svg)](https://react.dev/)
[![Boostrap 5.2](https://img.shields.io/badge/boostrap-5.2-blue.svg)](https://getbootstrap.com/docs/5.2/getting-started/introduction/)

NegoLog provides a web-based user interface to generate negotiation scenarios, create and edit tournament configurations, run and monitor tournaments. To run the web application, the following command line should be called:
```bash
python app.py
```

To specify port:
```bash
python app.py -p [PORT]
```

or 

```bash
python app.py -port [PORT]
```

## Development

### Agent Strategy
Agents aim to reach a joint decision within a limited time through negotiation without fully revealing their 
preferences. During negotiation, agents must decide what to offer and when to accept the opponent's offer. To
facilitate this process, *AbstractAgent* class provides a framework for developing negotiating agents. Each agent
must extend *AbstractAgent* class to implement its specific negotiation strategy.

**Components**:
Negotiating agents can be formulated as consisting of three main components [Baarslag *et al.* 2014](https://doi.org/10.1007/978-4-431-54758-7_4):
  - **Bidding Strategy**:  Determines what to offer.
  - **Acceptance Strategy**: Decides when to accept the opponent's offer
  - **Opponent Model**: Estimates the preferences of the opponent.

  By extending *AbstractAgent* class, *bidding strategy* and *acceptance strategy* are implemented to develop an agent.
  
> **Note**: To implement an opponent model, see also [*Opponent Model*](#opponent-model) development.

**Methods**:
To extend *AbstractAgent* class, following methods must be implemented:
  - **initiate**: Use this method to initialize required variables instead of the constructor.
  - **name**: Each agent must have a unique name for logging purposes.
  - **receive_offer**: This method is called when an offer is received. Generally, the opponent model can be updated in this method.
  - **act**: This method determines the action that the agent takes. It should include the *bidding strategy* and *acceptance strategy*.
  - **terminate**: This method is called at the end of the negotiation session.

### Opponent Model
Estimators (i.e., Opponent Model) predicts the opponent's preferences during a negotiation. Each Opponent Model
should be a subclass of *AbstractOpponentModel*. They should generate *EstimatedPreference* object which is the
predicted preferences of the opponent agent. 

This separated structure (from the agent strategy) enables to independently develop and evaluate preference estimators via *loggers*.

**Methods**:
To extend  *AbstractOpponentModel* class, following methods must be implemented:
  - **name**: Each estimator must have a unique name for logging purposes.
  - **update**: This method is called when an offer is received from the opponent.
  - **preference**: This method returns the estimated preferences of the opponent as an *EstimatedPreference* object.


### Custom Logger
NegoLog provides customizable **Analytics and Visualization Modules** called *logger* for advanced analysis, 
comprehensive logs and statistical graphs. **AbstractLogger** class, employing callback mechanisms, empowers 
researchers and developers to easily implement their own *loggers* within NegoLog.

> **Note**: Each *logger* must be a subclass of **AbstractLogger** class.

**Methods & Callbacks**:
  - **initiate**: Use this method to initialize required variables instead of the constructor.
  - **before_session_start**: This callback is invoked before each session starts.
  - **on_offer**: This callback is invoked when an offer is proposed. **Round-based** logs and analysis can be conducted in this method. This method should return logs as a dictionary for *session* log file.
  - **on_accept**:: This callback is invoked when the negotiation session ends **with** an agreement. This method should return logs as a dictionary for *session* log file.
  - **on_fail**: This callback is invoked when the negotiation session ends **without** any agreement. This method should return logs as a dictionary for *session* log file.
  - **on_session_end**: This callback is invoked after the negotiation session ends. **Session-based** logs and analysis can be conducted in this method. This method should return logs as a dictionary for *tournament* log file.
  - **on_tournament_end**: This callback is invoked after the tournament ends. **Tournament-based** logs, analysis and graph generation can be conducted in this method.
  - **get_path**: The directory path for logs & results.

## Citation

If you use our code in your research, please cite our paper:

```bibtex
@inproceedings{ijcai2024p998,
  title     = {NegoLog: An Integrated Python-based Automated Negotiation Framework with Enhanced Assessment Components},
  author    = {Doğru, Anıl and Keskin, Mehmet Onur and Jonker, Catholijn M. and Baarslag, Tim and Aydoğan, Reyhan},
  booktitle = {Proceedings of the Thirty-Third International Joint Conference on
               Artificial Intelligence, {IJCAI-24}},
  publisher = {International Joint Conferences on Artificial Intelligence Organization},
  editor    = {Kate Larson},
  pages     = {8640--8643},
  year      = {2024},
  month     = {8},
  note      = {Demo Track},
  doi       = {10.24963/ijcai.2024/998},
  url       = {https://doi.org/10.24963/ijcai.2024/998},
}
```

## License

NegoLog framework & library
Copyright (C) 2024 Anıl Doğru & M. Onur Keskin & Reyhan Aydoğan

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

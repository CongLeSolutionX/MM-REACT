"""Chain pipeline where the outputs of one step feed directly into next."""

from typing import Dict, List

from pydantic import BaseModel, Extra, root_validator

from langchain.chains.base import Chain
from langchain.input import get_color_mapping


class SequentialChain(Chain, BaseModel):
    """Chain where the outputs of one step feed directly into next."""

    chains: List[Chain]
    input_variables: List[str]
    output_variables: List[str]  #: :meta private:
    return_all: bool = False

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        """Expect input key.

        :meta private:
        """
        return self.input_variables

    @property
    def output_keys(self) -> List[str]:
        """Return output key.

        :meta private:
        """
        return self.output_variables

    @root_validator(pre=True)
    def validate_chains(cls, values: Dict) -> Dict:
        """Validate that the correct inputs exist for all chains."""
        chains = values["chains"]
        input_variables = values["input_variables"]
        known_variables = set(input_variables)
        for chain in chains:
            if missing_vars := set(chain.input_keys).difference(known_variables):
                raise ValueError(
                    f"Missing required input keys: {missing_vars}, "
                    f"only had {known_variables}"
                )
            if overlapping_keys := known_variables.intersection(chain.output_keys):
                raise ValueError(
                    f"Chain returned keys that already exist: {overlapping_keys}"
                )
            known_variables |= set(chain.output_keys)

        if "output_variables" not in values:
            output_keys = (
                known_variables.difference(input_variables)
                if values.get("return_all", False)
                else chains[-1].output_keys
            )
            values["output_variables"] = output_keys
        elif missing_vars := set(values["output_variables"]).difference(
            known_variables
        ):
            raise ValueError(
                f"Expected output variables that were not found: {missing_vars}."
            )
        return values

    def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
        known_values = inputs.copy()
        for chain in self.chains:
            outputs = chain(known_values, return_only_outputs=True)
            known_values |= outputs
        return {k: known_values[k] for k in self.output_variables}


class SimpleSequentialChain(Chain, BaseModel):
    """Simple chain where the outputs of one step feed directly into next."""

    chains: List[Chain]
    strip_outputs: bool = False
    input_key: str = "input"  #: :meta private:
    output_key: str = "output"  #: :meta private:

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        """Expect input key.

        :meta private:
        """
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        """Return output key.

        :meta private:
        """
        return [self.output_key]

    @root_validator()
    def validate_chains(cls, values: Dict) -> Dict:
        """Validate that chains are all single input/output."""
        for chain in values["chains"]:
            if len(chain.input_keys) != 1:
                raise ValueError(
                    "Chains used in SimplePipeline should all have one input, got "
                    f"{chain} with {len(chain.input_keys)} inputs."
                )
            if len(chain.output_keys) != 1:
                raise ValueError(
                    "Chains used in SimplePipeline should all have one output, got "
                    f"{chain} with {len(chain.output_keys)} outputs."
                )
        return values

    def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
        _input = inputs[self.input_key]
        color_mapping = get_color_mapping([str(i) for i in range(len(self.chains))])
        for i, chain in enumerate(self.chains):
            _input = chain.run(_input)
            if self.strip_outputs:
                _input = _input.strip()
            self.callback_manager.on_text(
                _input, color=color_mapping[str(i)], end="\n", verbose=self.verbose
            )
        return {self.output_key: _input}

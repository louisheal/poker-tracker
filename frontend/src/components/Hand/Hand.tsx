import type { HandDto } from "../../domain";

interface Props {
  hand: HandDto;
}

const HandDisplay = (props: Props) => {
  return (
    <>
      <h2>
        {props.hand.FstCard.Rank}
        {props.hand.FstCard.Suit}
        //
        {props.hand.SndCard.Rank}
        {props.hand.SndCard.Suit}
      </h2>
    </>
  );
};

export default HandDisplay;

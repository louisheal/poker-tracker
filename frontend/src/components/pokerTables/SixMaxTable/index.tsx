import Seat from "../Seat";
import Layout from "./Layout";

interface Props {
  btnPos: number;
}

const SixMaxTable = (props: Props) => {
  return (
    <Layout btnPos={props.btnPos}>
      <Seat label="" />
      <Seat label="" />
      <Seat label="You" />
      <Seat label="" />
      <Seat label="" />
      <Seat label="" />
    </Layout>
  );
};

export default SixMaxTable;

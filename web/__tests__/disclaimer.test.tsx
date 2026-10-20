import { render, screen } from "@testing-library/react";
import { Disclaimer } from "@/components/Disclaimer";

test("Disclaimer menampilkan teks", () => {
  render(<Disclaimer teks="bukan pengganti advokat" />);
  expect(screen.getByText(/bukan pengganti advokat/)).toBeInTheDocument();
});

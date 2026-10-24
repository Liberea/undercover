export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  return (
    <>
      <p className="back">
        <a href="#/">Claims queue</a>
      </p>
      <h1 className="mono">{claimId}</h1>
    </>
  );
}

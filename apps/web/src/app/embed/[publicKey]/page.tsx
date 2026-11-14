import Chat from "@/components/chat";
export default async function EmbedPage({
  params,
}: {
  params: Promise<{ publicKey: string }>;
}) {
  const { publicKey } = await params;
  return (
    <main className="embed-chat">
      <Chat publicKey={publicKey} />
    </main>
  );
}

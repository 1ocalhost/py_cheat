import re
import asyncio


all_clients = {}
re_http_forward_proxy = re.compile(
    r'^http://([^:/]+)(?::([^/]*))?/(.*)')


async def read_http_header(reader):
    header = b''
    while True:
        line = await reader.readline()
        if not line:
            return

        header += line
        if line == b'\r\n':
            break

    return header


async def get_request_info_from_header(reader):
    header = await read_http_header(reader)
    if not header:
        raise

    header_items = header.decode().split('\r\n')
    method_args = header_items[0].split(' ')
    method = method_args[0]
    uri = method_args[1]
    tunnel_mode = (method == 'CONNECT')
    print(method, uri)

    if tunnel_mode:
        remote_host = uri.split(':')
        host = remote_host[0]
        port = int(remote_host[1])
    else:
        m = re_http_forward_proxy.match(uri)
        if not m:
            raise

        host = m.group(1)
        port_str = m.group(2)
        port = int(port_str) if port_str else 80
        method_args[1] = '/' + m.group(3)
        header_items[0] = ' '.join(method_args)

    new_header = '\r\n'.join(header_items).encode()
    return new_header, tunnel_mode, (host, port)


async def relay_stream(read1, write1, read2, write2):
    async def relay(reader, writer):
        while True:
            line = await reader.read(1024)
            if len(line) == 0:
                break
            writer.write(line)
            await writer.drain()

    await asyncio.wait([
        relay(read1, write2),
        relay(read2, write1)
    ])


async def server_handler_impl(reader, writer):
    try:
        header, tunnel_mode, remote_host = \
            await get_request_info_from_header(reader)
        peer_reader, peer_writer = \
            await asyncio.open_connection(*remote_host)
    except Exception:
        return

    try:
        if tunnel_mode:
            writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
            await writer.drain()
        else:
            peer_writer.write(header)
            await peer_writer.drain()
        await relay_stream(reader, writer, peer_reader, peer_writer)
    finally:
        peer_writer.close()


async def server_handler(reader, writer):
    routine = server_handler_impl(reader, writer)
    task = asyncio.ensure_future(routine)
    all_clients[task] = (reader, writer)

    def client_done(task):
        del all_clients[task]
        writer.close()

    task.add_done_callback(client_done)


async def server_loop(host, port):
    def exception_handler(loop, context):
        if 'exception' in context:
            exception = context['exception']
            if isinstance(exception, OSError):
                return

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)

    server = await asyncio.start_server(server_handler, host, port)
    await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(server_loop('127.0.0.1', 9000))
